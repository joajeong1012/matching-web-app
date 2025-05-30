import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")
st.title("💘 레이디 이어주기 매칭 분석기 2.0")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

def parse_range(text):
    if pd.isna(text): return None, None
    text = str(text).replace("이하", "~1000").replace("이상", "0~").replace("-", "~").replace(" ", "")
    if "~" in text:
        parts = text.split("~")
        return float(parts[0] or 0), float(parts[1] or 999)
    else:
        try:
            val = float(text)
            return val, val
        except:
            return None, None

def is_in_range(val, range_text):
    try:
        val = float(val)
        min_val, max_val = parse_range(range_text)
        return min_val <= val <= max_val
    except:
        return False

def list_match(val, pref):
    if pd.isna(pref): return False
    prefs = [x.strip() for x in str(pref).split(",")]
    return "상관없음" in prefs or str(val).strip() in prefs

def overlap(list1, list2):
    a = [x.strip() for x in str(list1).split(",")]
    b = [x.strip() for x in str(list2).split(",")]
    return any(i in b for i in a)

def must_conditions_satisfied(a, b):
    musts = str(a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리":
            if a["희망하는 거리 조건"] == "단거리" and a["레이디의 거주 지역"] != b["레이디의 거주 지역"]:
                return False
        elif cond == "성격":
            if not list_match(b["성격(레이디)"], a["성격(상대방)"]): return False
        elif cond == "머리 길이":
            if not list_match(b["머리 길이(레이디)"], a["머리 길이(상대방)"]): return False
        elif cond == "데이트 주기":
            if not list_match(b["데이트 선호 주기"], a["데이트 선호 주기"]): return False
        elif cond == "흡연":
            if not list_match(b["[흡연(레이디)]"], a["[흡연(상대방 레이디)]"]): return False
        elif cond == "음주":
            if not list_match(b["[음주(레이디)]"], a["[음주(상대방 레이디) ]"]): return False
        elif cond == "타투":
            if not list_match(b["[타투(레이디)]"], a["[타투(상대방 레이디)]"]): return False
        elif cond == "벽장":
            if not list_match(b["[벽장(레이디)]"], a["[벽장(상대방 레이디)]"]): return False
        elif cond == "퀴어 지인 多":
            if not list_match(b["[퀴어 지인 多 (레이디)]"], a["[퀴어 지인 多 (상대방 레이디)]"]): return False
        elif cond == "앙큼 레벨":
            if not overlap(b["양금 레벨"], a["희망 양금 레벨"]): return False
        elif cond == "키":
            if not is_in_range(b["레이디 키"], a["상대방 레이디 키"]): return False
        elif cond == "연락 텀":
            if not list_match(b["[연락 텀(레이디)]"], a["[연락 텀(상대방 레이디)]"]): return False
    return True

def match_score(a, b):
    matched = []
    score = 0
    total = 0

    def add_score(cond, match):
        nonlocal score, total
        total += 1
        if match:
            score += 1
            matched.append(cond)

    # 나이
    add_score("A 나이 → B 선호", is_in_range(a["레이디 나이"], b["선호하는 상대방 레이디 나이"]))
    add_score("B 나이 → A 선호", is_in_range(b["레이디 나이"], a["선호하는 상대방 레이디 나이"]))

    # 키
    add_score("A 키 → B 선호", is_in_range(a["레이디 키"], b["상대방 레이디 키"]))
    add_score("B 키 → A 선호", is_in_range(b["레이디 키"], a["상대방 레이디 키"]))

    # 지역
    add_score("거리 조건", a["레이디의 거주 지역"] == b["레이디의 거주 지역"])

    # 기타 속성들
    for field in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多", "연락 텀", "머리 길이", "데이트 선호 주기", "성격"]:
        add_score(f"A {field}", list_match(a[f"[{field}(레이디)]"], b[f"[{field}(상대방 레이디)]"]))
        add_score(f"B {field}", list_match(b[f"[{field}(레이디)]"], a[f"[{field}(상대방 레이디)]"]))

    # 앙금 레벨
    add_score("앙금 레벨", overlap(a["양금 레벨"], b["희망 양금 레벨"]))

    return score, total, matched

if user_input:
    try:
        df = pd.read_csv(StringIO(user_input), sep="\t")
        df = df.dropna(how="all")
        df = df.fillna("")

        # 컬럼 정리
        df = df.rename(columns=lambda x: x.strip().replace("\n", "").replace("  ", " "))
        df = df.rename(columns={
            df.columns[1]: "닉네임",
            "레이디 키를 적어주she레즈 (숫자만 적어주세여자)": "레이디 키",
            "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)": "상대방 레이디 키",
            "성격 [성격(레이디)]": "성격(레이디)",
            "성격 [성격(상대방 레이디)]": "성격(상대방)",
            "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 맞아야 조건들",
            "레이디의 앙큼 레벨": "양금 레벨",
            "상대방 레이디의 앙큼 레벨": "희망 양금 레벨",
        })

        df["레이디 키"] = pd.to_numeric(df["레이디 키"], errors="coerce")
        df["레이디 나이"] = df["레이디 나이"].str.extract(r"(\d+)", expand=False).astype(float)

        matches = []
        seen = set()

        for i, j in permutations(df.index, 2):
            a, b = df.loc[i], df.loc[j]
            key = tuple(sorted([a["닉네임"], b["닉네임"]]))
            if key in seen: continue
            if must_conditions_satisfied(a, b) and must_conditions_satisfied(b, a):
                s, t, conds = match_score(a, b)
                percent = round(s / t * 100, 1) if t else 0
                matches.append({
                    "A 닉네임": a["닉네임"],
                    "B 닉네임": b["닉네임"],
                    "점수": f"{s}/{t}",
                    "비율(%)": percent,
                    "일치 조건": ", ".join(conds)
                })
                seen.add(key)

        result_df = pd.DataFrame(matches).sort_values(by="비율(%)", ascending=False)
        st.success("✅ 매칭 분석 완료!")
        st.dataframe(result_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
