import pandas as pd
import streamlit as st
from io import StringIO
from itertools import permutations

st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기 2.0")

user_input = st.text_area("📥 TSV 형식 응답 데이터를 붙여넣으세요", height=300)

def clean_columns(cols):
    return [c.strip().replace("\n", "").replace("  ", " ") for c in cols]

def parse_range(text):
    if pd.isna(text): return None, None
    text = str(text).strip()
    if text == "" or text == "~": return None, None
    text = text.replace("이하", "~1000").replace("이상", "0~")
    if '~' in text:
        parts = text.replace(' ', '').split('~')
        try:
            return float(parts[0]), float(parts[1])
        except:
            return None, None
    try:
        return float(text), float(text)
    except:
        return None, None

def is_in_range(val, range_text):
    try:
        val = float(val)
        min_val, max_val = parse_range(range_text)
        if min_val is None or max_val is None:
            return False
        return min_val <= val <= max_val
    except:
        return False

def is_preference_match(preference_value, target_value):
    if pd.isna(preference_value) or pd.isna(target_value):
        return False
    pref_list = [x.strip() for x in str(preference_value).split(",")]
    return "상관없음" in pref_list or str(target_value).strip() in pref_list

def list_overlap(list1, list2):
    return any(a.strip() in [b.strip() for b in list2] for a in list1 if a.strip())

def satisfies_must_conditions(a, b):
    musts = str(a.get("꼭 맞아야 하는 조건들은 무엇인가레?", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리":
            if a.get("희망하는 거리 조건", "").strip() == "단거리" and a.get("레이디의 거주 지역") != b.get("레이디의 거주 지역"):
                return False
        elif cond == "성격":
            if not is_preference_match(a.get("성격(상대방 레이디)", "상관없음"), b.get("성격(레이디)", "상관없음")):
                return False
        elif cond == "머리 길이":
            if not is_preference_match(a.get("머리 길이(상대방 레이디)", "상관없음"), b.get("머리 길이(레이디)", "상관없음")):
                return False
        elif cond == "키":
            if not is_in_range(b.get("레이디 키", 0), a.get("상대방 레이디 키")):
                return False
        elif cond == "흡연":
            if not is_preference_match(a.get("[흡연(상대방 레이디)]", "상관없음"), b.get("[흡연(레이디)]", "상관없음")):
                return False
        elif cond == "음주":
            if not is_preference_match(a.get("[음주(상대방 레이디) ]", "상관없음"), b.get("[음주(레이디)]", "상관없음")):
                return False
        elif cond == "타투":
            if not is_preference_match(a.get("[타투(상대방 레이디)]", "상관없음"), b.get("[타투(레이디)]", "상관없음")):
                return False
        elif cond == "벽장":
            if not is_preference_match(a.get("[벽장(상대방 레이디)]", "상관없음"), b.get("[벽장(레이디)]", "상관없음")):
                return False
        elif cond == "퀴어 지인 多":
            if not is_preference_match(a.get("[퀴어 지인 多 (상대방 레이디)]", "상관없음"), b.get("[퀴어 지인 多 (레이디)]", "상관없음")):
                return False
        elif cond == "데이트 주기":
            if not is_preference_match(a.get("[데이트 선호 주기]", "상관없음"), b.get("[데이트 선호 주기]", "상관없음")):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(str(a.get("상대방 레이디의 앙큼 레벨", "")).split(","), str(b.get("레이디의 앙큼 레벨", "")).split(",")):
                return False
    return True

if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        raw_df.columns = clean_columns(raw_df.columns)
        df = raw_df.dropna(how="all")

        # 숫자 처리
        df["레이디 키"] = pd.to_numeric(df["레이디 키를 적어주she레즈 (숫자만 적어주세여자)"], errors="coerce")
        df = df.rename(columns={
            "오늘 레개팅에서 쓰실 닉네임은 무엇인가레?  (오픈카톡 닉네임과 동(성)일 하게이 맞춰주she레즈)": "닉네임",
            "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)": "상대방 레이디 키",
            "성격 [성격(레이디)]": "성격(레이디)",
            "성격 [성격(상대방 레이디)]": "성격(상대방 레이디)",
            " [머리 길이(레이디)]": "머리 길이(레이디)",
            " [머리 길이(상대방 레이디)]": "머리 길이(상대방 레이디)",
        })

        matches = []
        for a_idx, b_idx in permutations(df.index, 2):
            a, b = df.loc[a_idx], df.loc[b_idx]
            if satisfies_must_conditions(a, b):
                matches.append({
                    "A": a["닉네임"],
                    "B": b["닉네임"],
                    "퍼센트": 100.0
                })

        result_df = pd.DataFrame(matches)
        if result_df.empty:
            st.warning("조건을 만족하는 매칭이 없습니다 😢")
        else:
            st.success("💖 매칭 결과")
            st.dataframe(result_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
