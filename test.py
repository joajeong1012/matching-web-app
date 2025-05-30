import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 꼭 맞는 레이디 매칭 분석기")
st.markdown("#### 📋 TSV 응답 데이터를 붙여넣어 주세요")

user_input = st.text_area("응답 붙여넣기 (TSV 형식)", height=300)

# 꼭 맞아야 조건 검사 함수들
def parse_range(text):
    try:
        text = str(text).strip().replace("이하", "~1000").replace("이상", "0~")
        if "~" in text:
            parts = text.split("~")
            start = float(parts[0]) if parts[0] else 0
            end = float(parts[1]) if parts[1] else 1000
            return start, end
        return float(text), float(text)
    except:
        return None, None

def is_in_range(value, range_text):
    try:
        val = float(value)
        min_val, max_val = parse_range(range_text)
        return min_val <= val <= max_val
    except:
        return False

def is_match(a, b, condition):
    if condition == "거리":
        if "단거리" in a["희망하는 거리 조건"]:
            return a["레이디의 거주 지역"] == b["레이디의 거주 지역"]
        return True
    if condition == "성격":
        return b["성격(레이디)"].strip() in a["성격(상대방)"].split(",")
    if condition == "머리 길이":
        return b["머리 길이(레이디)"].strip() in a["머리 길이(상대방)"].split(",")
    if condition == "앙큼 레벨":
        a_levels = set(map(str.strip, a["희망 양금 레벨"].split(",")))
        b_levels = set(map(str.strip, b["양금 레벨"].split(",")))
        return bool(a_levels & b_levels)
    if condition == "키":
        return is_in_range(b["레이디 키"], a["상대방 레이디 키"])
    return True

if user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep="\t")
        df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)
        df = df.rename(columns={
            df.columns[1]: "닉네임",
            "레이디 키를 적어주she레즈 (숫자만 적어주세여자)": "레이디 키",
            "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)": "상대방 레이디 키",
            "레이디의 앙큼 레벨": "양금 레벨",
            "상대방 레이디의 앙큼 레벨": "희망 양금 레벨",
            "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 맞아야 조건들",
        })

        st.success("✅ 데이터 업로드 완료!")
        with st.expander("📄 데이터 보기"):
            st.dataframe(df)

        results = []
        for i, j in permutations(df.index, 2):
            a = df.loc[i]
            b = df.loc[j]
            musts = list(map(str.strip, str(a.get("꼭 맞아야 조건들", "")).split(",")))
            if all(is_match(a, b, cond) for cond in musts if cond):
                results.append({
                    "A 닉네임": a["닉네임"],
                    "B 닉네임": b["닉네임"],
                    "꼭 맞아야 조건 수": len([c for c in musts if c]),
                    "매칭 조건": ", ".join(musts)
                })

        if results:
            st.subheader("💘 꼭 맞는 매칭 결과")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("❌ '꼭 맞아야 조건들'을 모두 만족하는 매칭이 없습니다.")

    except Exception as e:
        st.error(f"분석 실패: {e}")

