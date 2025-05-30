import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations

# ===================== UI 설정 ============================
st.set_page_config(page_title="레이디 매칭 분석기", layout="wide")

st.title("💘 레이디 이어주기 매칭 분석기 2.0")
st.markdown("#### 📋 구글 폼 응답을 복사해서 붙여넣어주세요 (TSV 형식)")
st.markdown("양식: 탭으로 구분된 데이터. 전체 응답 복사 → 붙여넣기")

user_input = st.text_area("📥 응답 데이터를 붙여넣으세요", height=300)

# ===================== 유틸 함수 ============================
def clean_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.dropna(axis=1, how="all")
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)

    pattern_map = {
        "닉네임": "닉네임",
        "레이디 나이": "레이디 나이",
        "선호하는 상대방 레이디 나이": "선호하는 상대방 레이디 나이",
        "레이디 키를 적어주she레즈": "레이디 키",
        "상대방 레이디 키를 적어주she레즈": "상대방 레이디 키",
        "레이디의 거주 지역": "레이디의 거주 지역",
        "희망하는 거리 조건": "희망하는 거리 조건",
        "[흡연(레이디)]": "흡연(레이디)",
        "[흡연(상대방 레이디)]": "흡연(상대방)",
        "[음주(레이디)]": "음주(레이디)",
        "[음주(상대방 레이디)]": "음주(상대방)",
        "[타투(레이디)]": "타투(레이디)",
        "[타투(상대방 레이디)]": "타투(상대방)",
        "[벽장(레이디)]": "벽장(레이디)",
        "[벽장(상대방 레이디)]": "벽장(상대방)",
        "성격 [성격(레이디)]": "성격(레이디)",
        "성격 [성격(상대방 레이디)]": "성격(상대방)",
        "[연락 텀(레이디)]": "연락 텀(레이디)",
        "[연락 텀(상대방 레이디)]": "연락 텀(상대방)",
        "[머리 길이(레이디)]": "머리 길이(레이디)",
        "[머리 길이(상대방 레이디)]": "머리 길이(상대방)",
        "[데이트 선호 주기]": "데이트 선호 주기(레이디)",
        "퀴어 지인 [레이디 ]": "퀴어 지인(레이디)",
        "퀴어 지인 [상대방 레이디]": "퀴어 지인(상대방)",
        "[퀴어 지인 多 (레이디)]": "퀴어 지인 多(레이디)",
        "[퀴어 지인 多 (상대방 레이디)]": "퀴어 지인 多(상대방)",
        "레이디의 앙큼 레벨": "양금 레벨",
        "상대방 레이디의 앙큼 레벨": "희망 양금 레벨",
        "꼭 맞아야 하는 조건들은 무엇인가레?": "꼭 맞아야 조건들"
    }

    for patt, std in pattern_map.items():
        hits = [c for c in df.columns if patt in c]
        if hits:
            df = df.rename(columns={hits[0]: std})

    for base in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多", "연락 텀", "머리 길이", "데이트 선호 주기", "성격"]:
        for suffix in ["(레이디)", "(상대방)"]:
            col = f"{base}{suffix}"
            if col not in df.columns:
                df[col] = "상관없음"

    df["레이디 키"] = pd.to_numeric(df.get("레이디 키", pd.Series(dtype=float)), errors="coerce")
    # df["레이디 나이"]는 float으로 바꾸지 않음 (범위 비교 위해)

    return df

def parse_range(text):
    try:
        if pd.isna(text): return None, None
        text = str(text).strip()
        if not text or text == "~": return None, None
        text = text.replace("이하", "~1000").replace("이상", "0~")
        if '~' in text:
            parts = text.replace(' ', '').split('~')
            return float(parts[0]), float(parts[1]) if len(parts) == 2 else (None, None)
        else:
            return float(text), float(text)
    except:
        return None, None

def is_in_range(val, range_text):
    try:
        if pd.isna(val): return False
        val = float(val)
        min_val, max_val = parse_range(range_text)
        if min_val is None or max_val is None:
            return False
        return min_val <= val <= max_val
    except:
        return False

def is_in_range_list(val, range_texts):
    return any(is_in_range(val, r.strip()) for r in str(range_texts).split(",") if r.strip())

def list_overlap(list1, list2):
    return any(a.strip() in [b.strip() for b in list2] for a in list1 if a.strip())

def is_preference_match(preference_value, target_value):
    if pd.isna(preference_value) or pd.isna(target_value):
        return False
    pref_list = [x.strip() for x in str(preference_value).split(",")]
    return "상관없음" in pref_list or str(target_value).strip() in pref_list

def satisfies_must_conditions(person_a, person_b):
    musts = str(person_a.get("꼭 맞아야 조건들", "")).split(",")
    for cond in musts:
        cond = cond.strip()
        if cond == "거리" and person_a.get("희망하는 거리 조건") == "단거리":
            if person_a.get("레이디의 거주 지역") != person_b.get("레이디의 거주 지역"):
                return False
        elif cond == "성격":
            if not is_preference_match(person_a.get("성격(상대방)", "상관없음"), person_b.get("성격(레이디)", "상관없음")):
                return False
        elif cond == "머리 길이":
            if not is_preference_match(person_a.get("머리 길이(상대방)", "상관없음"), person_b.get("머리 길이(레이디)", "상관없음")):
                return False
        elif cond == "앙큼 레벨":
            if not list_overlap(
                str(person_a.get("희망 양금 레벨", "")).split(","),
                str(person_b.get("양금 레벨", "")).split(",")
            ):
                return False
    return True

def match_score(a, b):
    score, total = 0, 0
    matched = []

    if is_in_range_list(a.get("레이디 키"), b.get("상대방 레이디 키")):
        score += 1
        matched.append("A 키 → B 선호")
    total += 1
    if is_in_range_list(b.get("레이디 키"), a.get("상대방 레이디 키")):
        score += 1
        matched.append("B 키 → A 선호")
    total += 1

    if is_in_range_list(a.get("레이디 나이"), b.get("선호하는 상대방 레이디 나이")):
        score += 2
        matched.append("A 나이 → B 선호")
    total += 1
    if is_in_range_list(b.get("레이디 나이"), a.get("선호하는 상대방 레이디 나이")):
        score += 2
        matched.append("B 나이 → A 선호")
    total += 1

    if a.get("희망하는 거리 조건") == "단거리" or b.get("희망하는 거리 조건") == "단거리":
        if a.get("레이디의 거주 지역") == b.get("레이디의 거주 지역"):
            score += 1
            matched.append("거리 일치 (단거리)")
        total += 1
    else:
        score += 1
        matched.append("거리 무관")
        total += 1

    for field in ["흡연", "음주", "타투", "벽장", "퀴어 지인 多"]:
        a_self = a.get(f"{field}(레이디)", "상관없음")
        a_wish = b.get(f"{field}(상대방)", "상관없음")
        b_self = b.get(f"{field}(레이디)", "상관없음")
        b_wish = a.get(f"{field}(상대방)", "상관없음")

        if is_preference_match(a_wish, a_self):
            score += 1
            matched.append(f"A {field}")
        total += 1
        if is_preference_match(b_wish, b_self):
            score += 1
            matched.append(f"B {field}")
        total += 1

    for field in ["연락 텀", "머리 길이", "데이트 선호 주기"]:
        r, d = field + "(레이디)", field + "(상대방)"
        if is_preference_match(b.get(d, "상관없음"), a.get(r, "상관없음")):
            score += 1
            matched.append(f"A {field}")
        total += 1
        if is_preference_match(a.get(d, "상관없음"), b.get(r, "상관없음")):
            score += 1
            matched.append(f"B {field}")
        total += 1

    if is_preference_match(b.get("성격(상대방)", "상관없음"), a.get("성격(레이디)", "상관없음")):
        score += 1
        matched.append("A 성격")
    total += 1
    if is_preference_match(a.get("성격(상대방)", "상관없음"), b.get("성격(레이디)", "상관없음")):
        score += 1
        matched.append("B 성격")
    total += 1

    if list_overlap(
        str(a.get("양금 레벨", "")).split(","),
        str(b.get("희망 양금 레벨", "")).split(",")
    ):
        score += 1
        matched.append("앙금 레벨")
    total += 1

    return score, total, matched

# ===================== 실행 ============================
if user_input:
    try:
        raw_df = pd.read_csv(StringIO(user_input), sep="\t")
        df = clean_df(raw_df)

        st.success("✅ 데이터 정제 완료!")
        with st.expander("🔍 정제된 데이터 보기"):
            st.dataframe(df)

        matches = []
        seen = set()
        for a, b in permutations(df.index, 2):
            pa, pb = df.loc[a], df.loc[b]
            pair = tuple(sorted([pa.get("닉네임"), pb.get("닉네임")]))
            if pair in seen: continue
            seen.add(pair)
            if not satisfies_must_conditions(pa, pb) or not satisfies_must_conditions(pb, pa):
                continue
            s, t, conds = match_score(pa, pb)
            percent = round((s / t) * 100, 1)
            matches.append({
                "A 닉네임": pair[0],
                "B 닉네임": pair[1],
                "매칭 점수": s,
                "총 점수": t,
                "비율(%)": percent,
                "요약": f"{s} / {t}점 ({percent}%)",
                "일치 조건들": ", ".join(conds)
            })

        result_df = pd.DataFrame(matches).sort_values(by="매칭 점수", ascending=False)
        st.subheader("💘 매칭 결과")
        if result_df.empty:
            st.warning("😢 매칭 조건을 만족하는 결과가 없습니다.")
        else:
            st.dataframe(result_df)

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
