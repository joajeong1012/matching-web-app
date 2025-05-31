import pandas as pd
import streamlit as st
import re
from io import StringIO
from itertools import permutations

st.set_page_config(page_title="💘 레이디 이어주기 매칭 분석기 3.1", layout="wide")

st.title("🌈 레이디 이어주기 매칭 분석기 3.1")
st.markdown("#### 📋 구글폼 응답 결과를 TSV (탭 구분 데이터) 형식으로 붙여넣어주세요")
st.markdown("전체 응답 복사 → 아래 텍스트박스에 붙여넣기")

user_input = st.text_area("📅 응답 데이터를 빠지여넣으세요", height=300)

if user_input:
    try:
        data = pd.read_csv(StringIO(user_input), sep="\t", engine="python")
        data.columns = data.columns.str.replace(r"\s+", " ", regex=True).str.strip()
        data.columns = data.columns.str.replace("\n", " ")

        # 닉네임 컬럼 자동 인식
        possible_nick_cols = [col for col in data.columns if "닉네임" in col or "쓰실 닉네임" in col]
        if not possible_nick_cols:
            st.error("❌ '닉네임'이라는 말이 포함된 컬럼명을 찾을 수 없어요! 헤더에 줄바꿈이 들어간 건 아닌지 확인해주세요.")
            st.stop()
        nickname_col = possible_nick_cols[0]

        data = data.drop_duplicates(subset=nickname_col)
        data = data[data[nickname_col].notna() & (data[nickname_col].astype(str).str.strip() != "")]

        results = []
        required_col = "꼭 맞아야 하는 조건들은 무엇인가레?"

        for a, b in permutations(data.to_dict(orient="records"), 2):
            a_nick = str(a.get(nickname_col)).strip()
            b_nick = str(b.get(nickname_col)).strip()
            if not a_nick or not b_nick:
                continue

            score = 0
            reasons = []
            total = 0

            for col in data.columns:
                if "레이디" in col and "(상대방" in col:
                    my_val = a.get(col)
                    your_val = b.get(col.replace("레이디", "상대방 레이디"))

                    if pd.isna(my_val) or pd.isna(your_val):
                        continue

                    my_list = re.split(r"[,\s]+", str(my_val).strip())
                    your_list = re.split(r"[,\s]+", str(your_val).strip())
                    if not my_list or not your_list:
                        continue

                    total += 1
                    if any(item in your_list for item in my_list):
                        score += 1
                        reasons.append(col.split()[0])

            required = str(a.get(required_col, "")).strip()
            required_items = re.split(r"[,\s]+", required)
            for cond in required_items:
                if cond == "":
                    continue
                if cond not in reasons:
                    score = 0
                    total = 0
                    reasons = ["❌ 꼭 맞아야 하는 조건 불일치"]
                    break

            percent = round(score / total * 100, 2) if total > 0 else 0.0

            results.append({
                "A": a_nick,
                "B": b_nick,
                "궁합 점수": f"{score} / {total}",
                "퍼센트(%)": percent,
                "매칭 사유 요약": ", ".join(reasons)
            })

        result_df = pd.DataFrame(results)
        result_df = result_df.sort_values("퍼센트(%)", ascending=False)

        st.success(f"총 {len(result_df)}쌍 매칭 완료 🎉")
        st.dataframe(result_df, use_container_width=True)

        csv = result_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 결과 CSV 다운로드", data=csv, file_name="lady_matching_results.csv", mime='text/csv')

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("👀 데이터를 붙여넣으면 자동 분석이 시작됩니다!")

