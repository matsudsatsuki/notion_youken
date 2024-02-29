import streamlit as st
from notion_client import Client
import datetime
from openai import OpenAI
from dotenv import load_dotenv
import os

# 環境変数をロード
load_dotenv()

# 環境変数から情報を取得
USERNAME = st.secrets["username"]
PASSWORD = st.secrets["password"]
NOTION_API_KEY = st.secrets["notion_api_key"]
OPENAI_API_KEY = st.secrets["openai_api_key"]

# スタイルのカスタマイズ
st.markdown(""" 
<style>
    .css-18e3th9 {
        padding-top: 0rem;
        padding-bottom: 10rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    .stSidebar > div:first-child {
        background-color: #f0f2f6;
    }
    .css-1d391kg {
        padding-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)
# セッションステートで認証状態を管理
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# 認証済みでない場合はログインフォームを表示
if not st.session_state['authenticated']:
    with st.container():
        st.header("ログイン")
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")

        if st.button('ログイン'):
            if username == USERNAME and password == PASSWORD:
                st.session_state['authenticated'] = True
                st.rerun()  # 認証後、ページをリロード
            else:
                st.error("認証に失敗しました。")

# 認証済みの場合はアプリケーションのメインコンテンツを表示
if st.session_state['authenticated']:
    if "proposal_generated" not in st.session_state:
        st.session_state.proposal_generated = False
    def is_form_data_insufficient(section):
        for field in section["fields"]:
            # st.session_stateにフィールドのキーが存在し、かつその値が空でないことを確認
            if field["key"] not in st.session_state or not st.session_state[field["key"]]:
                return True
        return False
    # Notionに送信するデータを準備する際に、セクション定義で使用されたキーを使用する
    def create_notion_page(notion, database_id, form_data):
        # 現在の日付をYYYY-MM-DD形式で取得
        today_date = datetime.datetime.now().date().isoformat()

        new_page_data = {
            "parent": {"database_id": database_id},
            "properties": {
            # 作成日プロパティに現在の日付を設定
            "作成日": {
                "date": {
                    "start": today_date
                }
            }
        }
        }
        for key, value in form_data.items():
            if value:
                if key == "プロジェクト名":
                    new_page_data["properties"]["プロジェクト名"] = {"title": [{"text": {"content": value}}]}
                else:
                    new_page_data["properties"][key] = {"rich_text": [{"text": {"content": value}}]}

        response = notion.pages.create(**new_page_data)
        st.write(response)
        return response


    # Notion APIクライアントを初期化
    notion = Client(auth=NOTION_API_KEY)

    # アプリケーションのタイトル設定
    st.title("要件定義書作成フォーム")

    # プログレスバーの初期化
    progress_bar = st.progress(0)
    #
    # フォームデータを更新する関数
    def update_form_data():
        # 既存のform_dataをそのまま保持し、新しい入力値で更新
        for section in sections:
            for field in section["fields"]:
                # この時点での入力をセッションステートに保存
                st.session_state[field["key"]] = st.session_state.get(field["key"], "")
                # form_dataには、すべてのセッションステートから集めたデータを保持
                st.session_state.form_data[field["key"]] = st.session_state[field["key"]]


    # フォームデータと現在のステップの初期化
    if "form_data" not in st.session_state:
        st.session_state.form_data = {}
    if "current_step" not in st.session_state:
        st.session_state.current_step = 0
    if "dummy_questions_added" not in st.session_state:
        st.session_state.dummy_questions_added = False

    # フォームの各セクション定義
    sections = [
        {"title": "プロジェクトの概要", "fields": [
            {"label": "プロジェクト名", "placeholder": "任意：新しいウェブサイト構築など", "key": "プロジェクト名",
            "help": "「プロジェクト名」は、プロジェクトを簡潔に表す名称です。例えば、「新しいウェブサイト構築」や「社内システムの改善」など、プロジェクトの目的がわかる名前をつけてください。"},
            {"label": "プロジェクトの目的", "placeholder": "オンラインでの商品販売促進", "key": "プロジェクトの目的", "multiline": True, 
            "help": "このプロジェクトで何を達成したいか、簡潔に記述してください。例えば、「オンライン販売の拡大」や「顧客管理システムの効率化」など、具体的な目標を設定します。"},
            {"label": "開発背景", "placeholder": "市場拡大と顧客の要望に応えるため", "key": "開発背景", "multiline": True, 
            "help": "このプロジェクトを始めた理由や背景を記述してください。市場の変化、顧客からの要望、内部の業務改善の必要性など、プロジェクト開始の動機を共有します。"},
        ]},
        {"title": "業務の範囲", "fields": [
            {"label": "対象とする業務の概要", "placeholder": "商品の在庫管理とオンラインでの注文受付", "key": "対象とする業務の概要", "multiline": True,
            "help": "プロジェクトによって改善または影響を受ける業務の範囲を記述してください。具体的な業務プロセスや対象となる業務領域について説明します。"},
            {"label": "主な業務プロセス", "placeholder": "注文受付 → 在庫確認 → 発送", "key": "主な業務プロセス", "multiline": True, 
            "help": "プロジェクトが対象とする主要な業務プロセスを、ステップごとに記述してください。例: 「注文受付 → 在庫確認 → 発送」のように、プロセスの流れを明確にします。"}
        ]},
        {"title": "システムの範囲", "fields": [
            {"label": "必要とする主要機能", "placeholder": "顧客管理、在庫管理、注文管理", "key": "必要とする主要機能", "multiline": True, 
            "help": "このプロジェクトで実装または改善が必要なシステムの機能を記述してください。例えば、「顧客管理」「在庫管理」「注文管理」など、必要な機能をリストアップします。"},
            {"label": "ユーザーインターフェースの希望", "placeholder": "ウェブブラウザからアクセス可能なウェブアプリケーション", "key": "ユーザーインターフェースの希望", "multiline": True, 
            "help": "ユーザーがシステムとどのようにやり取りするか、希望するユーザーインターフェース（UI）の種類を記述してください。ウェブアプリケーション、モバイルアプリ、デスクトップアプリなど。"},
            {"label": "外部システムとの連携", "placeholder": "決済サービス（Stripe等）との連携", "key": "外部システムとの連携", "multiline": True, 
            "help": "このシステムが連携する外部システムやサービスについて記述してください。例えば、決済サービス（Stripe等）、CRMシステム、在庫管理システムなど。"}
        ]},
        {"title": "非機能要件", "fields": [
            {"label": "パフォーマンス要件", "placeholder": "1秒以内のレスポンスタイム", "key": "パフォーマンス要件", "multiline": True,
            "help": "システムが満たすべきパフォーマンス基準を記述してください。例:「レスポンスタイムは1秒以内」など、ユーザーの快適な使用感を確保するための要件。"},
            {"label": "セキュリティ要件", "placeholder": "顧客情報の暗号化", "key": "セキュリティ要件", "multiline": True,
            "help": "システムのセキュリティに関する要件を記述してください。例えば、「顧客情報の暗号化」や「二段階認証の導入」など、情報保護のための措置。"},
        ]},
        {"title": "開発・運用・保守の要件", "fields": [
            {"label": "スケジュールの希望", "placeholder": "3ヶ月以内にローンチ", "key": "スケジュールの希望", "multiline": True, 
            "help": "プロジェクトの期間やマイルストーンに関する希望を記述してください。例:「3ヶ月以内にローンチ」「6ヶ月で基本機能の開発完了」など。"},
            {"label": "予算の範囲", "placeholder": "最大200万円", "key": "予算の範囲", "multiline": True,
            "help": "プロジェクトの予算に関する希望を記述してください。例:「最大200万円」「月額10万円以内」など。"},
            {"label": "テスト・移行計画の希望", "placeholder": "ユーザーテストを1ヶ月行う", "key": "テスト・移行計画の希望", "multiline": True, 
            "help": "システムのテストや既存システムからの移行計画に関する希望を記述してください。ユーザーテストの実施期間や移行のスケジュールなど。"},
            {"label": "教育・サポートの要望", "placeholder": "操作マニュアルの作成とスタッフトレーニング", "key": "教育・サポートの要望", "multiline": True,
            "help": "ユーザー教育やサポート体制に関する要望を記述してください。操作マニュアルの作成、スタッフトレーニングの実施など。"}
        ]},
        {"title": "その他コメント・要望", "fields": [
            {"label": "特記事項やその他の要望", "placeholder": "利用開始後6ヶ月間の無料サポート希望", "key": "特記事項やその他の要望", "multiline": True,
            "help": "上記のカテゴリに含まれないその他のコメントや要望を自由に記述してください。例えば、特定の技術の使用希望、特別なサポート条件など。"}
        ]}
    ]
    def initialize_session_state():
        for section in sections:
            for field in section["fields"]:
                if field["key"] not in st.session_state:
                    st.session_state[field["key"]] = ""
        if "current_step" not in st.session_state:
            st.session_state["current_step"] = 0

    initialize_session_state()

    # セクション名のリストを作成
    section_names = [section["title"] for section in sections]

    # サイドバーにセクションのナビゲーションを表示
    st.sidebar.markdown("## セクション")
    for i, section_name in enumerate(section_names):
        num = i + 1
        if i == st.session_state.current_step:
            # 現在のセクションには強調表示
            
            if st.sidebar.button(f"→ {num}. {section_name} (現在)", key=f"btn_current_{i}"):
                st.session_state.current_step = i
                st.rerun()
        else:
            # 他のセクションへの移動ボタン
            if st.sidebar.button(f"{i+1}. {section_name}", key=f"btn_{i}"):
                st.session_state.current_step = i
                st.rerun()

    current_section_index = st.session_state.current_step
    current_section = sections[current_section_index]

    # プログレスバーの更新
    progress_percentage = (current_section_index + 1) / len(sections)
    progress_bar.progress(progress_percentage)
    # セッションステートで送信状態を管理
    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    # 送信後の完了画面表示関数
    def show_completion_screen():
        st.success("あなたの要件定義書が無事に無事に送信されました！")
        st.balloons()  # 送信の成功を祝うアニメーション
        st.markdown("### ありがとうございます！")
        st.markdown("何か他に必要な情報があれば、お気軽にお問い合わせください。")
        st.markdown("また、このフォームは何度でも送信できます。")
        
        # フォームを再送信したい場合のために、セッションステートをリセットする機能を追加
        col1, col2,col3 = st.columns([1,3,1])
        with col1:
            if st.button("リセット"):
                st.session_state.submitted = False
                st.session_state.current_step = 0
                for key in st.session_state.form_data.keys():
                    del st.session_state[key]
                st.rerun()
        with col3:
            # 提案書作成機能のボタンを右端に配置
            if st.button("提案書を作成(β版)"):
                # create_proposal_document()
                st.session_state.proposal_generated = True
                # st.rerun()
        # テキスト用のスペースを作成
        if st.session_state.proposal_generated:
            st.markdown("## 提案書ドラフト")
            st.write("提案書のドラフトがGPT-3によって生成されます。")
            
       # GPTのAPIキーを設定
    def generate_proposal_content(form_data):
        
        client = OpenAI(api_key="OPENAI_API_KEY")
        # フォームデータをテキストに変換
        form_data_text = "\n".join([f"{key}: {value}" for key, value in form_data.items()])

        # 新しいAPIインターフェイスを使用してGPT-3にテキスト生成を依頼
        response = client.chat.completions.create(model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "以下の要件に基づいて提案書のドラフトを作成してください。何も入力がない場合は、その旨をお知らせください。"},
                {"role": "user", "content": form_data_text}
            ])
        
        # 生成されたテキストを返す
        return response.choices[0].message.content

    def create_proposal_document():
        # フォームデータから提案書内容を生成
        # time.sleep(1)  # 1秒待機
        proposal_content = generate_proposal_content(st.session_state.form_data)
        # 提案書のドラフトを表示
        st.markdown("## 提案書ドラフト")
        st.write(proposal_content)

    def display_section(section):
        st.header(section["title"])
        # セクションごとにヘルプテキストを表示するボタンを追加
        if st.button(f"{section['title']}の記述例を表示"):
            st.markdown(f"### {section['title']}の記述例")
            for field in section["fields"]:
                st.info(field.get("help", "ヘルプ情報がここに表示されます。"))
        
        for field in section["fields"]:
            if field.get("multiline"):
                st.text_area(label=field["label"], key=field["key"], placeholder=field["placeholder"])
            else:
                st.text_input(label=field["label"], key=field["key"], placeholder=field["placeholder"])

    def save_form_data():
        # 現在のセクションのデータをform_dataに保存
        current_section = sections[st.session_state.current_step]
        for field in current_section["fields"]:
            field_key = field["key"]
            # print(field_key)
            # セッションステートから値を取得し、form_dataに保存
            st.session_state.form_data[field_key] = st.session_state.get(field_key, "")
            # print(st.session_state.form_data)

    def navigate_sections():
        current_section = sections[st.session_state.current_step]
        display_section(current_section)

        col1, col2, col3 = st.columns([1,5,1])
        with col1:
            if st.button("戻る") and st.session_state.current_step > 0:
                st.session_state.current_step -= 1
                st.rerun()

        with col3:
            if st.session_state.current_step < len(sections) - 1:
                if st.button("次へ"):
                    save_form_data()
                    st.session_state.current_step += 1
                    st.rerun()
            else:
                if st.button("送信"):
                    save_form_data()  # 最終セクションのデータを保存
                    # ウィジェットの入力を直接form_dataに集約
                    form_data = st.session_state.form_data
                    response = create_notion_page(notion, "affb1ff20fa04a92b161ab3e6f80b456", form_data)
                    if response:
                        st.session_state.submitted = True  # 送信成功フラグをセット
                        st.success("要件定義書がNotionに記録されました！")
                        # form_dataとcurrent_stepのリセット
                        st.session_state.current_step = 0
                        for key in form_data.keys():
                            del st.session_state[key]  # 各キーの値をクリア
                        st.rerun()
                    else:
                        st.error("要件定義書の記録に失敗しました。")
                    
    # 追加情報を提供する質問を表示    
    # 送信が完了したかどうかを確認し、完了画面を表示
    if st.session_state.submitted:
        show_completion_screen()
    else:
        navigate_sections()
          # 通常のセクションナビゲーションとフォーム表示
        
    def show_additional_assistance():
        if st.session_state.get('show_assistance', False):
            additional_goal = st.text_input("あなたのプロジェクトで最も重要な目標は何ですか？", key="additional_goal")
            if st.button("追加情報を送信"):
                st.session_state.form_data["additional_goal"] = additional_goal
                st.success("追加情報を受け取りました。ありがとうございます！")
                st.session_state.show_assistance = False
    # show_additional_assistance()
    # navigate_sections()