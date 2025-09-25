# ScholarBot

**🌐 言語 | Language:** [English](README.md) | **日本語**

> **注意:** 最も正確で最新の情報については、[English版](README.md)をご参照ください。

学術論文の分析、洞察の抽出、関連研究の発見を行う強力なAIボット。FastAPI、LangChain、OpenAI、Slack Bot統合で構築されています。

## 🚀 機能

- **PDFの処理**: PDFファイルやURLからテキストを抽出・分析
- **AI搭載の要約**: 最先端のLLM（GPT-4）を使用した包括的な論文要約
- **関連論文の発見**: Semantic Scholar APIを使用して意味的に類似した研究論文を発見
- **FastAPI Webサーバー**: 自動ドキュメント生成機能付きのモダンな非同期Web API
- **Slack統合**: チームコラボレーションのためのWebhookベースのSlack統合
- **ngrokサポート**: 開発とテストのための簡単なパブリックURL公開
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

2. **APIキー**
   
   **必須キー（基本機能に必要）:**
   - **Jina AI APIキー**: [Jina AI](https://jina.ai/)から取得 - PDFテキスト抽出に必要
   - **Slack Botトークン**: Slackアプリを作成してbotトークンを取得 - Slack連携に必要
   - **Slack署名シークレット**: Slackアプリ設定から取得 - Webhook検証に必要
   
   **LLMプロバイダーキー（少なくとも1つ選択）:**
   - **OpenAI APIキー**: [OpenAI Platform](https://platform.openai.com/api-keys)から取得 - GPT-4モデル用
   - **Google Gemini APIキー**: [Google AI Studio](https://aistudio.google.com/)から取得 - Geminiモデル用
   - **Google Cloud認証情報**: Vertex AI アクセス用 - [Google Cloud Console](https://console.cloud.google.com/)からサービスアカウントJSONをダウンロード
   - **Anthropic APIキー**: [Anthropic Console](https://console.anthropic.com/)から取得 - Claudeモデル用
   
   **オプションキー:**
   - **LangChain APIキー**: [LangChain](https://smith.langchain.com/)から取得 - 会話トレーシングとデバッグ用

### 設定

1. **環境変数**
   プロジェクトルートに`.env`ファイルを作成:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
   SLACK_SIGNING_SECRET=your-slack-signing-secret
   JINA_API_KEY=your_jina_api_key
   OPENAI_API_KEY=your_openai_api_key  # OpenAIを使用する場合
   GOOGLE_API_KEY=your_gemini_api_key  # Google Gemini APIを使用する場合
   GOOGLE_APPLICATION_CREDENTIALS=path_to_your_vertexai_credential_json # Google VertexAI APIを使用する場合
   ANTHROPIC_API_KEY=your_anthropic_api_key  # Anthropic APIを使用する場合
   LANGCHAIN_API_KEY=your_langchain_api_key  # トレーシング用（オプション）
   ```

2. **Slackアプリの設定**
   - [api.slack.com](https://api.slack.com/apps)で新しいSlackアプリを作成
   - **重要**: このアプリはイベント処理にSlack BoltとWebhookエンドポイントを使用します
   - Bot Token Scopes を追加: `app_mentions:read`, `chat:write`, `files:read`
   - Event Subscriptionsを設定:
     - Eventsを有効化し、Request URLをngrokトンネル + `/slack/events`に設定
     - `app_mention`イベントにサブスクライブ
   - Interactivityを設定:
     - Interactivityを有効化し、Request URLをngrokトンネル + `/slack/interactions`に設定
   - ワークスペースにアプリをインストール
   - Bot User OAuth TokenとSigning Secret（Basic Informationから）をコピー

## 🚀 使用方法

### サーバーの起動

**オプション1: 起動スクリプトを使用（推奨）**
```bash
python start_server.py
```

**オプション2: 手動起動**
```bash
# FastAPIサーバーを起動
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000

# 別のターミナルでngrokを起動（オプション）
ngrok http 8000
```

**オプション3: 自動リロード付き開発モード**
```bash
python start_server.py --reload
```

起動スクリプトは以下を実行します:
- Slack Bolt Webhookエンドポイント付きでポート8000のFastAPIサーバーを起動
- ngrokトンネルを自動起動（`--no-ngrok`が指定されない限り）
- Slack Webhook設定用のパブリックURLを表示

**注意**: WebhookモードではSlackがローカル開発サーバーにアクセスするためngrok（または類似サービス）が必要です。

### エージェントの使用

1. **Slackコマンド**
   - `@YourBot https://arxiv.org/pdf/2301.00000.pdf この論文を要約して` - PDFを分析・要約
   - `@YourBot 先ほど共有した論文に関連する論文を見つけて` - Semantic Scholarで類似研究を発見
   - `@YourBot /new 今度はこの論文を要約して https://...` - 新しい会話を開始（以前の文脈をクリア）
   - `@YourBot /select_llm_provider` - 好みのLLMプロバイダーを選択（ChatGPT、Google、...）

2. **利用可能エンドポイント**（監視/デバッグ用）
   - `GET /health` - ヘルスチェックと現在の設定
   - `GET /slack/status` - Slack接続ステータス
   - `GET /docs` - FastAPI自動ドキュメント

3. **対応操作**
   - PDF URLやPDFファイルと一緒に質問を共有
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
- [x] Webhook統合を使用したFastAPI Webサーバー
- [x] Event Subscriptionsを使用したSlack統合
- [x] 開発用のngrokトンネルサポート
- [x] 多言語対応と自動検出
- [x] スレッド管理によるメモリ対応会話
- [x] ファイルアップロード対応（URL以外）
- [x] 複数のモデルプロバイダー対応
- [ ] エラーハンドリングと検証の強化
- [ ] AWS/GCPへのデプロイ
- [ ] Slackの代替となるWebインターフェース
- [ ] 複数論文のバッチ処理

## 🤝 コントリビューション

お気軽に以下をお願いします:
- バグの報告
- 新機能の提案
- プルリクエストの送信
- ドキュメントの改善
