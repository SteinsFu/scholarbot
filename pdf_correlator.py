import requests
from io import BytesIO
import hashlib
import os
from tqdm import tqdm
import re
from typing import List, Optional
import fitz
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
from torch.utils.tensorboard import SummaryWriter



# TODO: remove this temporary list
PDF_LIST = {
    "FlowEdit: Inversion-Free Text-Based Editing Using Pre-Trained Flow Models": "https://arxiv.org/pdf/2412.08629",
    "Stable Flow: Vital Layers for Training-Free Image Editing": "https://arxiv.org/pdf/2411.14430",
    "Manifold Diffusion Fields": "https://arxiv.org/pdf/2305.15586",
    "Image Interpolation with Score-based Riemannian Metrics of Diffusion Models": "https://arxiv.org/pdf/2504.20288",
    "SDEdit: Guided Image Synthesis and Editing with Stochastic Differential Equations": "https://arxiv.org/pdf/2108.01073",
    "Flow Matching for Generative Modeling": "https://arxiv.org/pdf/2210.02747",
    "Prompt-to-Prompt Image Editing with Cross Attention Control": "https://arxiv.org/pdf/2208.01626",
    "Null-text Inversion for Editing Real Images using Guided Diffusion Models": "https://arxiv.org/pdf/2211.09794",
}




# ===== Functions for Downloading & Extracting Text =====
def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name).strip("._-")
    return name or "file"


def download_file(title: str, url: str, cache_dir: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    filename = f"{sanitize_filename(title)}.pdf"
    dest_path = os.path.join(cache_dir, filename)
    # If the (non-empty) file already exists, return the path
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return dest_path
    # Download the PDF from the URL by chunks to avoid memory issues
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest_path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=f"Downloading {filename[:20]}...") as pbar:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
    return dest_path


def extract_text_from_pdf(pdf_path: str) -> str:
    text_parts: List[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    text = "\n".join(text_parts)
    text = re.sub(r"\s+", " ", text)
    return text.strip()




# ===== Functions for Creating Embeddings =====
def chunk_text(text: str, max_chars: int = 1000) -> List[str]:
    if not text:
        return [""]
    paragraphs = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    buffer: List[str] = []
    current_len = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) + 1 > max_chars and buffer:
            chunks.append(" ".join(buffer))
            buffer = [para]
            current_len = len(para)
        else:
            buffer.append(para)
            current_len += len(para) + 1
    if buffer:
        chunks.append(" ".join(buffer))
    return chunks


def load_model(model_name: str, device: Optional[str]) -> SentenceTransformer:
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():    # For Apple Silicon (Mac)
            device = "mps"
        else:
            device = "cpu"
    model = SentenceTransformer(model_name, device=device)
    return model


def compute_document_embedding(text: str, model: SentenceTransformer, batch_size: int = 16) -> np.ndarray:
    chunks = chunk_text(text)
    if not chunks:
        chunks = [text]
    embeddings = model.encode(chunks, batch_size=batch_size, convert_to_numpy=True, show_progress_bar=False)
    doc_embedding = embeddings.mean(axis=0)
    return doc_embedding


def embed_documents(documents: List[str], model_name: str = "sentence-transformers/all-MiniLM-L6-v2", 
                    device: Optional[str] = None, batch_size: int = 16) -> np.ndarray:
    model = load_model(model_name, device)
    vectors = []
    for text in tqdm(documents, desc="Embedding documents"):
        vectors.append(compute_document_embedding(text, model, batch_size=batch_size))
    return np.vstack(vectors)


# ===== Functions for Similarity Calculation =====
def calculate_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    # Normalize embeddings for cosine similarity
    normalized_embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
    # Calculate cosine similarity matrix
    similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
    return similarity_matrix


def rank_similarity(pdf_name: str, embeddings: np.ndarray, paper_names: List[str]) -> List[tuple]:
    """
    Rank papers by similarity to the given PDF.
    
    Args:
        pdf_name: Name of the PDF to find similar papers for
        embeddings: numpy array of shape (n_documents, embedding_dim)
        paper_names: List of paper names corresponding to embeddings
        
    Returns:
        List of tuples (paper_name, similarity_score) ranked by similarity (descending)
    """
    # Find the index of the target PDF
    try:
        target_idx = paper_names.index(pdf_name)
    except ValueError:
        raise ValueError(f"PDF '{pdf_name}' not found in paper_names")
    
    similarity_matrix = calculate_similarity_matrix(embeddings)
    target_similarities = similarity_matrix[target_idx]
    similarity_tuples = [(paper_names[i], target_similarities[i]) for i in range(len(paper_names))]
    similarity_tuples.sort(key=lambda x: x[1], reverse=True)
    return similarity_tuples



# ===== Functions for TensorBoard =====
def create_tensorboard_embedding(embeddings: np.ndarray, metadata: List[str], log_dir: str = "tensorboard_logs"):
    writer = SummaryWriter(log_dir)
    writer.add_embedding(
        embeddings,
        metadata=[label for label in metadata],
        # label_img=embedding_images,
        # global_step=0,
        tag='pdf_embedding'
    )
    writer.close()
    print(f"TensorBoard embedding created in {log_dir}")
    print(f"Run `tensorboard --logdir {log_dir}` to view the embedding")



def main():
    pdf_paths = []
    for paper_title, paper_url in PDF_LIST.items():
        pdf_path = download_file(paper_title, paper_url, "pdfs")
        pdf_paths.append(pdf_path)
    
    labels = [filename.split("/")[-1].split(".")[0] for filename in pdf_paths]
    texts = [extract_text_from_pdf(pdf_path) for pdf_path in pdf_paths]
    embeddings = embed_documents(texts)
    
    # Calculate similarity matrix
    similarity_matrix = calculate_similarity_matrix(embeddings)
    print(f"Similarity matrix shape: {similarity_matrix.shape}")
    
    # Example: Rank papers by similarity to the first paper
    if labels:
        target_paper = labels[0]
        print(f"\nRanking papers by similarity to: {target_paper}")
        similar_papers = rank_similarity(target_paper, embeddings, labels)
        
        for i, (paper_name, similarity) in enumerate(similar_papers):
            print(f"{i+1}. {paper_name}: {similarity:.4f}")
    
    create_tensorboard_embedding(embeddings, labels)



if __name__ == "__main__":
    main()