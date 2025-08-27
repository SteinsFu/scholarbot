# Boost Papers Agent

**🌐 言語 | Language:** [English](README.md) | **日本語**

> **注意:** 最も正確で最新の情報については、[English版](README.md)をご参照ください。

学術論文の分析、洞察の抽出、関連研究の発見を行う強力なAIエージェント。最先端の言語モデルとPDF処理機能を使用しています。

## 🚀 機能

- **PDFの処理**: PDFファイルやURLからテキストを抽出・分析
- **AI搭載の要約**: 最先端のLLMを使用した包括的な論文要約
- **関連論文の発見**: 意味的に類似した研究論文を見つける
- **Slackインテグレーション**: チームコラボレーションのためのSlackとのシームレスな連携
- **3D可視化**: 論文の埋め込みと相関のインタラクティブな可視化
- その他...？

## 🛠️ セットアップ

### オプション1: Difyクラウドサービス（推奨）

1. **アカウント作成**
   - [Dify Cloud](https://cloud.dify.ai/apps)にアクセスしてアカウントを登録

2. **プラグインの設定**
   - **設定** → **プラグイン**に移動
   - 以下のプラグインをインストール:
     - `Jina AI`
     - `Gemini` 
     - `OpenAI`
     - `Slack Bot`

3. **APIキーの設定**
   - **OpenAI/Gemini**: **設定** → **モデルプロバイダー**でAPIキーを入力
   - **Jina AI**: [jina.ai](https://jina.ai/)からAPIキーを取得し、プラグインの認証フィールドで設定

4. **エージェントのインポート**
   - **スタジオ**タブに移動
   - **DSLファイルをインポート**をクリックして`dify_dsl/boost-papers-agent.yaml`をアップロード

### オプション2: ローカルDifyサーバー

1. **Dockerのインストール**
   - **Ubuntu**: [Docker Engineインストールガイド](https://docs.docker.com/engine/install/ubuntu/)に従う
   - **macOS/Windows**: [Docker Desktop](https://www.docker.com/products/docker-desktop)をダウンロード

2. **Difyのデプロイ**
   ```bash
   git clone https://github.com/langgenius/dify.git
   cd dify/docker
   cp .env.example .env
   sudo docker compose up -d
   ```

3. **アクセスと設定**
   - ブラウザで`http://localhost`を開く
   - アカウントを作成し、上記のオプション1のステップ2-4に従う

## 🎯 Difyアプリの使用方法

セットアップが完了したら:

1. **アプリの公開**
   - Difyで**公開**ボタンをクリック
   - 必要に応じて公開設定を行う
   - 公開を確認

2. **エージェントの使用開始**
   - **アプリを実行**をクリックしてチャットインターフェースを開く
   - PDFファイルをアップロードまたはPDF URLを提供
   - 論文について質問したり要約を依頼
   - 関連研究論文を発見

## 📋 開発状況

- [x] PDF URL入力処理
- [x] PDFファイルアップロード対応
- [x] PDFからのテキスト抽出
- [x] LLM搭載の論文要約
- [x] 関連論文の発見
- [ ] 論文に関するフォローアップ質問の許可
- [ ] AWS/GCPへのデプロイ
- [ ] Slackインテグレーション（AWS/GCPセットアップが必要な場合があります）
- [ ] PDF埋め込み可視化
- [ ] エラーハンドリングの強化
- [ ] Python を使用して関連論文を発見する代替案？

*さらなる機能の追加にご協力ください！*

## 🔬 PDF埋め込み可視化

*進行中: PyTorch文埋め込みを使用したPDFの意味的相関のインタラクティブ3D可視化。*

### 前提条件
```bash
conda create -n boost-proj python=3.12
conda activate boost-proj
pip install -r requirements.txt
```

### 使用方法

**埋め込みの生成:**
```bash
python pdf_correlator.py
```

**結果の可視化:**
```bash
tensorboard --logdir tensorboard_logs
```

## 🤝 コントリビューション

お気軽に以下をお願いします:
- バグの報告
- 新機能の提案
- プルリクエストの送信
- ドキュメントの改善
