# ScholarBot

**🌐 言語 | Language:** [English](README.md) | **日本語**

> **注意:** 最も正確で最新の情報については、[English版](README.md)をご参照ください。

学術論文の分析、洞察の抽出、関連研究の発見を行う強力なAIボット。LangChain、OpenAI、Slack Bot統合で構築されています。

## 🚀 機能

- **PDFの処理**: PDFファイルやURLからテキストを抽出・分析
- **AI搭載の要約**: 最先端のLLM（GPT-4）を使用した包括的な論文要約
- **関連論文の発見**: Semantic Scholar APIを使用して意味的に類似した研究論文を発見
- **Slackインテグレーション**: チームコラボレーションのためのSlackとのシームレスな連携
- **多言語対応**: 自動言語検出とユーザーの言語での応答
- **メモリ対応会話**: 文脈を理解したフォローアップ質問と議論

## 🛠️ セットアップ

### 前提条件

1. **Python環境**
   ```bash
   conda create -n scholarbot python=3.12
   conda activate scholarbot
   pip install -r requirements.txt
   ```

2. **必要なAPIキー**
   - **OpenAI APIキー**: [OpenAI Platform](https://platform.openai.com/api-keys)から取得
   - **Jina AI APIキー**: [Jina AI](https://jina.ai/)から取得
   - **Slack Botトークン**: Slackアプリを作成してbotトークンを取得
   - **Slack Appトークン**: Socket Modeを有効にしてアプリレベルトークンを取得

### 設定

1. **環境変数**
   プロジェクトルートに`.env`ファイルを作成:
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   JINA_API_KEY=your_jina_api_key
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_APP_TOKEN=xapp-your-slack-app-token
   LANGCHAIN_API_KEY=your_langchain_api_key  # トレーシング用（オプション）
   ```

2. **Slackアプリの設定**
   - [api.slack.com](https://api.slack.com/apps)で新しいSlackアプリを作成
   - Socket Modeを有効化
   - Bot Token Scopes を追加: `app_mentions:read`, `chat:write`, `files:read`
   - ワークスペースにアプリをインストール
   - Bot User OAuth TokenとApp-Level Tokenをコピー

## 🚀 使用方法

### Slack Botの実行

```bash
python app.py
```

### エージェントの使用

1. **Slackでボットをメンション**
   - `@YourBot https://arxiv.org/pdf/2301.00000.pdf この論文を要約して`
   - `@YourBot 先ほど共有した論文に関連する論文を見つけて`
   - `@YourBot /new 新しい会話を始めよう`

2. **対応コマンド**
   - PDF URLと一緒に質問を共有
   - 論文の要約を依頼
   - 関連論文の発見を要求
   - 以前に分析した論文に関するフォローアップ質問

### 動作中の機能

- **自動言語検出**: ボットはあなたのクエリと同じ言語で応答
- **文脈メモリ**: 各ユーザーはフォローアップ質問用の独自の会話スレッドを持つ
- **リッチレスポンス**: 整形された論文要約と関連論文のランキング

## 📋 開発状況

- [x] PDF URL入力処理
- [x] PDFファイルアップロード対応（Slack経由）
- [x] PDFからのテキスト抽出
- [x] LLM搭載の論文要約（GPT-4）
- [x] 関連論文の発見（Semantic Scholar API）
- [x] Socket Modeを使用したSlackインテグレーション
- [x] 多言語対応と自動検出
- [x] スレッド管理によるメモリ対応会話
- [ ] エラーハンドリングと検証の強化
- [ ] ファイルアップロード対応（URL以外）
- [ ] AWS/GCPへのデプロイ
- [ ] Slackの代替となるWebインターフェース
- [ ] 複数論文のバッチ処理

## 🤝 コントリビューション

お気軽に以下をお願いします:
- バグの報告
- 新機能の提案
- プルリクエストの送信
- ドキュメントの改善
