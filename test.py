import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

st.set_page_config(page_title="🌈 레이디 이어주기 궁합 분석기", layout="wide")

st.title("💘 레이디 이어주기 궁합 분석기 3.0")
st.markdown("구글폼 TSV 결과를 복사해서 붙여넣어주세요. 자동으로 예쁘게 분석해드려요 😚")

user_input = st.text_area("📥 TSV 데이터를 복붙해주세요", height=300)

if st.button("✨ 궁합 분석 시작하기"):
    try:
        # 🧹 줄바꿈, 공백 제거
        cleaned_input = user_input.replace("\r", "").replace('\n\n', '\n').replace('\n', ' ').replace('\t ', '\t')
        df = pd.read_csv(StringIO(cleaned_input), sep='\t')

        # 컬럼명 정리
        df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()

        # 닉네임 컬럼 찾기
        nickname_col = [col for col in df.columns if "닉네임" in col][0]
        df.rename(columns={nickname_col: "닉네임"}, inplace=True)

        # 꼭 맞아야 조건들
        def extract_must_conditions(val):
            if pd.isna(val): return []
            return [v.strip() for v in str(val).split(',') if v.strip()]
        
        results = []
        pairs = list(permutations(df.index, 2))
        
        for i, j in pairs:
            a, b = df.loc[i], df.loc[j]
            score = 0
            total = 0
            reasons = []
            must_a = extract_must_conditions(a.get("꼭 맞아야 하는 조건들은 무엇인가레?", ""))
            must_b = extract_must_conditions(b.get("꼭 맞아야 하는 조건들은 무엇인가레?", ""))

            for col in df.columns:
                col = col.strip()
                if col in ["닉네임", "타임스탬프"]: continue

                val_a = str(a.get(col, "")).strip()
                val_b = str(b.get(col, "")).strip()
                if not val_a or not val_b: continue

                # 긴/짧 항목 중복 허용 고려
                match = (
                    any(v in val_b for v in val_a.split(',')) or 
                    any(v in val_a for v in val_b.split(','))
                )

                is_must = col in must_a or col in must_b

                if match:
                    score += 1
                    reasons.append(f"✅ {col}")
                elif is_must:
                    score = 0
                    reasons = [f"❌ {col} (필수 조건 불일치)"]
                    break
                total += 1

            percent = round(score / total * 100 if total else 0, 1)
            results.append({
                "A": a["닉네임"],
                "B": b["닉네임"],
                "궁합 점수": f"{score} / {total}",
                "퍼센트(%)": percent,
                "매칭 사유 요약": ", ".join(reasons)
            })

        result_df = pd.DataFrame(results).sort_values("퍼센트(%)", ascending=False)
        st.success(f"총 {len(result_df)}쌍 매칭 완료 🎉")
        st.dataframe(result_df, use_container_width=True)

        # CSV 다운로드
        csv = result_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 결과 CSV 다운로드", data=csv, file_name="lady_matching_results.csv", mime='text/csv')

    except Exception as e:
        st.error(f"❌ 분석 실패: {str(e)}")
