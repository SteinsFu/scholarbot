#!/usr/bin/env python3
"""
Demo script to show cost savings from text optimization.
"""

import os
from pdf_utils import pdf_url_to_text
from text_optimizer import TextOptimizer

def demo_cost_savings():
    """Demonstrate cost savings with different optimization strategies."""
    
    # Example PDF URLs (you can change these)
    test_pdfs = [
        "https://arxiv.org/pdf/2505.11128.pdf",  # A recent paper
        "https://arxiv.org/pdf/2210.02747.pdf",  # Flow Matching paper
    ]
    
    print("=" * 80)
    print("PDF TEXT OPTIMIZATION COST DEMO")
    print("=" * 80)
    
    for i, pdf_url in enumerate(test_pdfs, 1):
        print(f"\n📄 Testing PDF {i}: {pdf_url}")
        print("-" * 60)
        
        try:
            # Test different strategies
            strategies = ["none", "smart", "sections", "truncate"]
            
            for strategy in strategies:
                if strategy == "none":
                    result = pdf_url_to_text(pdf_url, optimize=False)
                else:
                    result = pdf_url_to_text(pdf_url, optimize=True, strategy=strategy, max_tokens=3000)
                
                opt_info = result["optimization_info"]
                text = result["text"]
                
                print(f"\n🔧 Strategy: {strategy.upper()}")
                
                if strategy == "none":
                    # Calculate original stats
                    optimizer = TextOptimizer()
                    tokens = optimizer.count_tokens(text)
                    cost_info = optimizer.estimate_cost(text)
                    print(f"   📊 Tokens: {tokens:,}")
                    print(f"   💰 Estimated cost: ${cost_info['total_cost']:.4f}")
                    print(f"   📝 Text length: {len(text):,} characters")
                    original_cost = cost_info['total_cost']
                    original_tokens = tokens
                else:
                    tokens = opt_info.get('optimized_tokens', 0)
                    cost_info = opt_info.get('optimized_cost', {})
                    total_cost = cost_info.get('total_cost', 0)
                    reduction = opt_info.get('token_reduction', 0)
                    reduction_pct = opt_info.get('reduction_percentage', 0)
                    cost_savings = opt_info.get('cost_savings', 0)
                    
                    print(f"   📊 Tokens: {tokens:,} (reduced by {reduction:,})")
                    print(f"   📉 Token reduction: {reduction_pct:.1f}%")
                    print(f"   💰 Estimated cost: ${total_cost:.4f}")
                    print(f"   💵 Cost savings: ${cost_savings:.4f}")
                    print(f"   📝 Text length: {len(text):,} characters")
                    
                    if hasattr(locals(), 'original_cost') and original_cost > 0:
                        savings_pct = (cost_savings / original_cost) * 100
                        print(f"   📈 Cost reduction: {savings_pct:.1f}%")
                
                # Show a preview of the optimized text
                preview = text[:200] + "..." if len(text) > 200 else text
                print(f"   📖 Preview: {preview}")
                
        except Exception as e:
            print(f"❌ Error processing PDF: {e}")
    
    print("\n" + "=" * 80)
    print("💡 OPTIMIZATION TIPS:")
    print("=" * 80)
    print("""
1. 'smart' strategy: Best balance of quality and cost savings
2. 'sections' strategy: Preserves key academic sections
3. 'truncate' strategy: Simple truncation with beginning/end preservation
4. 'chunk' strategy: Process large documents in smaller pieces
5. 'auto' strategy: Automatically selects the best approach

For most academic papers, 'smart' or 'auto' strategies provide 50-80% cost savings
while preserving the most important information for summarization.
    """)


def test_chunking_strategy():
    """Test the chunking strategy for very large documents."""
    print("\n" + "=" * 80)
    print("CHUNKING STRATEGY DEMO")
    print("=" * 80)
    
    pdf_url = "https://arxiv.org/pdf/2210.02747.pdf"  # A longer paper
    
    try:
        result = pdf_url_to_text(pdf_url, optimize=True, strategy="chunk", max_tokens=3000)
        
        if "chunks" in result["optimization_info"]:
            chunks = result["optimization_info"]["chunks"]
            print(f"📦 Document split into {len(chunks)} chunks")
            
            optimizer = TextOptimizer()
            total_cost = 0
            
            for i, chunk in enumerate(chunks):
                tokens = optimizer.count_tokens(chunk)
                cost_info = optimizer.estimate_cost(chunk)
                chunk_cost = cost_info['total_cost']
                total_cost += chunk_cost
                
                print(f"   Chunk {i+1}: {tokens:,} tokens, ${chunk_cost:.4f}")
            
            print(f"\n💰 Total cost for chunked processing: ${total_cost:.4f}")
            
            # Compare with non-chunked
            original_result = pdf_url_to_text(pdf_url, optimize=False)
            original_text = original_result["text"]
            original_cost_info = optimizer.estimate_cost(original_text)
            original_cost = original_cost_info['total_cost']
            
            print(f"💰 Original cost (single request): ${original_cost:.4f}")
            print(f"💵 Additional cost for chunking: ${total_cost - original_cost:.4f}")
            print(f"📊 Cost ratio: {total_cost/original_cost:.2f}x")
            
            print("\n📝 Chunking is useful when:")
            print("  - Document is too large for single API call")
            print("  - You want to process sections independently")
            print("  - You need to stay within token limits")
        
    except Exception as e:
        print(f"❌ Error testing chunking: {e}")


if __name__ == "__main__":
    demo_cost_savings()
    test_chunking_strategy()
