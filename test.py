from itertools import permutations
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ===================== UI =====================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")

with st.container():
    st.title("💘 레이디 이어주기 매칭 분석기 2.0")
    st.caption("by ChatGPT 4.0")
    st.markdown("#### 📋 구글 폼 응답을 TSV 형식으로 복사해서 붙여넣어주세요")

user_input = st.text_area("📥 TSV 데이터 입력", height=300, placeholder="여기에 복사한 데이터를 붙여넣어주세요")

if user_input:
    try:
        from io import StringIO
        raw_data = StringIO(user_input)
        df = pd.read_csv(raw_data, sep='\t')
        df.columns = df.columns.str.strip().str.replace('\n', ' ', regex=False)

        st.success("✅ 데이터 업로드 성공!")
        st.dataframe(df, use_container_width=True)

        nickname_col = [col for col in df.columns if "닉네임" in col][0]
        preference_col = [col for col in df.columns if "꼭 맞아야" in col][0]

        df = df[[nickname_col, preference_col] + [col for col in df.columns if col not in [nickname_col, preference_col]]]
        df = df.drop_duplicates(subset=[nickname_col])

        results = []
        nicknames = df[nickname_col].tolist()

        for a, b in permutations(nicknames, 2):
            row_a = df[df[nickname_col] == a].iloc[0]
            row_b = df[df[nickname_col] == b].iloc[0]

            score = 0
            total = 0
            reason = []

            must_match_a = str(row_a[preference_col]).split(', ')
            must_match_b = str(row_b[preference_col]).split(', ')
            all_must = list(set(must_match_a + must_match_b))
            match_flag = True

            for col in all_must:
                col = col.strip()
                if col and col in df.columns:
                    val_a = str(row_a[col]).strip()
                    val_b = str(row_b[col]).strip()
                    if val_a != "" and val_b != "":
                        total += 1
                        if val_a == val_b:
                            score += 1
                        else:
                            match_flag = False
                            reason.append(f"❌ {col}")

            percent = round(score / total * 100, 1) if total > 0 else 0
            summary = " / ".join(reason) if not match_flag else "💖 조건 일치!"

            results.append({
                "A": a, "B": b,
                "궁합 점수": f"{score} / {total}",
                "퍼센트(%)": percent,
                "매칭 사유 요약": summary
            })

        result_df = pd.DataFrame(results)

        st.divider()
        st.markdown("## 🔍 매칭 결과")
        st.dataframe(result_df, use_container_width=True)

        st.divider()
        st.markdown("## 📊 궁합 점수 히트맵")
        pivot_df = result_df.pivot(index="A", columns="B", values="퍼센트(%)")
        fig, ax = plt.subplots(figsize=(10, 8))
        cax = ax.matshow(pivot_df.fillna(0), cmap='coolwarm')
        plt.xticks(range(len(pivot_df.columns)), pivot_df.columns, rotation=90)
        plt.yticks(range(len(pivot_df.index)), pivot_df.index)
        plt.colorbar(cax)
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("👆 위에 TSV 데이터를 붙여넣어주세요.")
