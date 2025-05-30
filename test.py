import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기 3.0")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
st.markdown("양식: 탭으로 구분된 데이터. 전체 응답 복사 → 붙여넣기")

user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

if user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep="\t")

        df = df.rename(columns={
            df.columns[1]: "닉네임",
            "레이디 키를 적어주she레즈 (숫자만 적어주세여자)": "레이디 키",
            "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)": "상대방 레이디 키",
            "레이디의 앙큼 레벨": "양금 레벨",
            "상대방 레이디의 앙큼 레벨": "희망 양금 레벨",
            "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 맞아야 조건들",
            "성격 [성격(레이디)]": "성격(레이디)",
            "성격 [성격(상대방 레이디)]": "성격(상대방)",
            " [머리 길이(레이디)]": "머리 길이(레이디)",
            " [머리 길이(상대방 레이디)]": "머리 길이(상대방)"
        })

        def is_preference_match(preference_value, target_value):
            if pd.isna(preference_value) or pd.isna(target_value):
                return False
            pref_list = [x.strip() for x in str(preference_value).split(",")]
            return "상관없음" in pref_list or str(target_value).strip() in pref_list

        def satisfies_conditions(a, b):
            conds = str(a.get("꼭 맞아야 조건들", "")).split(",")
            for cond in conds:
                cond = cond.strip()
                if cond == "거리":
                    if a["희망하는 거리 조건\n"] == "단거리" and a["레이디의 거주 지역"] != b["레이디의 거주 지역"]:
                        return False
                elif cond == "성격":
                    if not is_preference_match(a.get("성격(상대방)"), b.get("성격(레이디)")):
                        return False
                elif cond == "머리 길이":
                    if not is_preference_match(a.get("머리 길이(상대방)"), b.get("머리 길이(레이디)")):
                        return False
                elif cond == "앙큼 레벨":
                    if not any(x.strip() in str(b.get("양금 레벨", "")) for x in str(a.get("희망 양금 레벨", "")).split(",")):
                        return False
                elif cond == "키":
                    try:
                        a_height = float(a["레이디 키"])
                        b_range = str(b["상대방 레이디 키"])
                        for part in b_range.split(","):
                            part = part.strip().replace("이하", "~1000").replace("이상", "0~")
                            if "~" in part:
                                low, high = part.split("~")
                                if low and high and float(low) <= a_height <= float(high):
                                    break
                        else:
                            return False
                    except:
                        return False
            return True

        results = []
        for i, a in df.iterrows():
            for j, b in df.iterrows():
                if i >= j:
                    continue
                if satisfies_conditions(a, b) and satisfies_conditions(b, a):
                    results.append({
                        "A": a["닉네임"],
                        "B": b["닉네임"],
                        "꼭 맞는 조건": a["꼭 맞아야 조건들"]
                    })

        st.subheader("💘 꼭 맞는 사람들")
        if results:
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("❌ 꼭 맞는 조건을 만족하는 사람이 없어요!")

    except Exception as e:
        st.error(f"분석 실패: {e}")

