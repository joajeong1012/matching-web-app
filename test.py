import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import combinations

# ----------------- UI -----------------
st.set_page_config(page_title="💘 전체 조건 매칭기", layout="wide")
st.title("💘 전체 조건 기반 레이디 매칭기")
st.caption("TSV 전체 붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=300)
run = st.button("🔍 분석 시작")
st.markdown("---")

# ----------------- helpers -----------------
SEP = re.compile(r"[,/]|\s+")
WILDCARD_PAT = re.compile(r"(상관\s*없|무관|상관x|상관\s*x|상관무)", re.IGNORECASE)

def tokens(val):
    s = "" if val is None or (isinstance(val, float) and pd.isna(val)) else str(val)
    return [t.strip() for t in SEP.split(s) if t.strip()]

def clean_column(col: str) -> str:
    # 따옴표/개행/중복공백 제거
    s = str(col).replace("\n", " ").strip().strip('"\'' )
    s = re.sub(r"\s+", " ", s)
    return s

def norm(s: str) -> str:
    # 공백/대소문자/대괄호에 덜 민감하게
    return re.sub(r"\s+", "", str(s)).lower()

def find_column(df, *candidates):
    cols = list(df.columns)
    nmap = {norm(c): c for c in cols}
    # 1) 완전일치 우선
    for cand in candidates:
        nc = norm(cand)
        if nc in nmap:
            return nmap[nc]
    # 2) 부분일치
    for cand in candidates:
        key = norm(cand)
        for c in cols:
            if key in norm(c):
                return c
    return None

def parse_ranges_generic(val, upper_default=100.0):
    """숫자/범위를 리스트[(start,end)]로. '상관X'는 0~upper_default로."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    txt = str(val)
    if WILDCARD_PAT.search(txt):
        return [(0.0, float(upper_default))]

    parts = [v.strip() for v in txt.split(",") if v.strip()]
    out = []
    for part in parts:
        p = part
        p = p.replace("세 이상", "~100").replace("세이상", "~100")
        p = p.replace("세 이하", "0~").replace("세이하", "0~")
        keep = re.sub(r"[^\d~]", "", p)
        if "~" in keep:
            try:
                s, e = keep.split("~", 1)
                s = float(s or 0)
                e = float(e or upper_default)
                out.append((s, e))
            except:
                continue
        else:
            try:
                v = float(keep)
                out.append((v, v))
            except:
                continue
    return out

def ranges_overlap(val1, val2, upper_default=100.0):
    r1 = parse_ranges_generic(val1, upper_default)
    r2 = parse_ranges_generic(val2, upper_default)
    if not r1 or not r2:
        return False
    for s1, e1 in r1:
        for s2, e2 in r2:
            if max(s1, s2) <= min(e1, e2):
                return True
    return False

def distance_match(a_self, a_pref, b_self, b_pref):
    # 단거리만 요구하는 쪽이 있으면 지역 동일해야 함
    a_self = "" if a_self is None or (isinstance(a_self, float) and pd.isna(a_self)) else str(a_self)
    a_pref = "" if a_pref is None or (isinstance(a_pref, float) and pd.isna(a_pref)) else str(a_pref)
    b_self = "" if b_self is None or (isinstance(b_self, float) and pd.isna(b_self)) else str(b_self)
    b_pref = "" if b_pref is None or (isinstance(b_pref, float) and pd.isna(b_pref)) else str(b_pref)

    a_tokens = set(tokens(a_pref))
    b_tokens = set(tokens(b_pref))
    a_short_only = "단거리" in a_tokens and "장거리" not in a_tokens
    b_short_only = "단거리" in b_tokens and "장거리" not in b_tokens
    if a_short_only or b_short_only:
        return a_self.strip().lower() == b_self.strip().lower() and a_self.strip() != ""
    return True

# ----------------- main -----------------
if run and raw_text:
    try:
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = [clean_column(c) for c in df.columns]

        # ===== 실제 데이터 헤더에 맞춘 매핑 =====
        NICK = find_column(df, "닉네임")
        AGE_SELF = find_column(df, "레이디 나이")  # 그대로 존재
        AGE_PREF = find_column(df, "상대방 레이디 나이")  # 주신 헤더명
        DIST_SELF = find_column(df, "레이디의 거주 지역")  # 주신 헤더명
        DIST_PREF = find_column(df, "희망하는 거리 조건")  # 따옴표/개행 제거 후 매칭

        HEIGHT_SELF = find_column(df, "레이디 키")
        HEIGHT_PREF = find_column(df, "상대방 레이디 키")

        SMOKE_SELF = find_column(df, "흡연(레이디)", "[흡연(레이디)]")
        SMOKE_PREF = find_column(df, "흡연(상대방 레이디)", "[흡연(상대방 레이디)]")

        DRINK_SELF = find_column(df, "음주(레이디)", "[음주(레이디)]")
        DRINK_PREF = find_column(df, "음주(상대방 레이디)", "[음주(상대방 레이디)]", "[음주(상대방 레이디) ]")

        TATTOO_SELF = find_column(df, "타투(레이디)", "[타투(레이디)]")
        TATTOO_PREF = find_column(df, "타투(상대방 레이디)", "[타투(상대방 레이디)]")

        CLOSET_SELF = find_column(df, "벽장(레이디)", "[벽장(레이디)]")
        CLOSET_PREF = find_column(df, "벽장(상대방 레이디)", "[벽장(상대방 레이디)]")

        PERS_SELF = find_column(df, "성격(레이디)", "[성격(레이디)]")
        PERS_PREF = find_column(df, "성격(상대방 레이디)", "[성격(상대방 레이디)]")

        CONTACT_SELF = find_column(df, "연락 텀(레이디)", "[연락 텀(레이디)]")
        CONTACT_PREF = find_column(df, "연락 텀(상대방 레이디)", "[연락 텀(상대방 레이디)]")

        HAIR_SELF = find_column(df, "머리 길이(레이디)", "[머리 길이(레이디)]")
        HAIR_PREF = find_column(df, "머리 길이(상대방 레이디)", "[머리 길이(상대방 레이디)]")

        DATE_FREQ = find_column(df, "데이트 선호 주기", "[데이트 선호 주기]")

        if not NICK:
            st.error("❌ '닉네임' 컬럼을 찾을 수 없습니다. TSV 헤더를 확인하세요.")
        else:
            df = df[df[NICK].notna()].drop_duplicates(subset=[NICK]).reset_index(drop=True)

            condition_fields = {
                "나이": (AGE_SELF, AGE_PREF),
                "키": (HEIGHT_SELF, HEIGHT_PREF),
                "거리": (DIST_SELF, DIST_PREF),
                "흡연": (SMOKE_SELF, SMOKE_PREF),
                "음주": (DRINK_SELF, DRINK_PREF),
                "타투": (TATTOO_SELF, TATTOO_PREF),
                "벽장": (CLOSET_SELF, CLOSET_PREF),
                "성격": (PERS_SELF, PERS_PREF),
                "연락 텀": (CONTACT_SELF, CONTACT_PREF),
                "머리 길이": (HAIR_SELF, HAIR_PREF),
                "데이트 주기": (DATE_FREQ, DATE_FREQ),
            }

            # 존재하는 조건만 사용
            all_conditions = [k for k, (self_c, pref_c) in condition_fields.items() if self_c and pref_c]

            results = []
            for i, j in combinations(df.index, 2):
                A, B = df.loc[i], df.loc[j]
                a_nick, b_nick = str(A[NICK]).strip(), str(B[NICK]).strip()
                matched = 0
                issues = []

                for key in all_conditions:
                    a_field, b_field = condition_fields[key]
                    a_self = A.get(a_field, "")
                    a_pref = A.get(b_field, "")
                    b_self = B.get(a_field, "")
                    b_pref = B.get(b_field, "")

                    if key == "나이":
                        ok1 = ranges_overlap(b_self, a_pref, upper_default=100.0)  # B의 나이가 A의 선호에
                        ok2 = ranges_overlap(a_self, b_pref, upper_default=100.0)  # A의 나이가 B의 선호에
                        if ok1 and ok2: matched += 1
                        else:
                            if not ok1: issues.append("A의 나이 조건 불일치")
                            if not ok2: issues.append("B의 나이 조건 불일치")

                    elif key == "키":
                        ok1 = ranges_overlap(b_self, a_pref, upper_default=300.0)
                        ok2 = ranges_overlap(a_self, b_pref, upper_default=300.0)
                        if ok1 and ok2: matched += 1
                        else:
                            if not ok1: issues.append("A의 키 조건 불일치")
                            if not ok2: issues.append("B의 키 조건 불일치")

                    elif key == "거리":
                        ok = distance_match(a_self, a_pref, b_self, b_pref)
                        if ok: matched += 1
                        else: issues.append("거리 조건 불일치")

                    else:
                        tok_a = set(tokens(a_self))
                        tok_ap = set(tokens(a_pref))
                        tok_b = set(tokens(b_self))
                        tok_bp = set(tokens(b_pref))
                        a_ok = bool(tok_ap & tok_b)
                        b_ok = bool(tok_bp & tok_a)
                        if a_ok and b_ok: matched += 1
                        else:
                            if not a_ok: issues.append(f"A의 {key} 조건 불일치")
                            if not b_ok: issues.append(f"B의 {key} 조건 불일치")

                total = len(all_conditions)
                match_rate = round(matched / total * 100, 1) if total else 0.0

                # 표시용 개별 플래그
                age_ok = (AGE_SELF and AGE_PREF) and (
                    ranges_overlap(A.get(AGE_SELF), B.get(AGE_PREF), 100.0) and
                    ranges_overlap(B.get(AGE_SELF), A.get(AGE_PREF), 100.0)
                )
                dist_ok = (DIST_SELF and DIST_PREF) and distance_match(
                    A.get(DIST_SELF), A.get(DIST_PREF), B.get(DIST_SELF), B.get(DIST_PREF)
                )

                results.append({
                    "A ↔ B": f"{a_nick} ↔ {b_nick}",
                    "전체 조건 일치율 (%)": match_rate,
                    "나이 일치": "✅" if age_ok else ("❌" if age_ok is False else "정보없음"),
                    "거리 일치": "✅" if dist_ok else ("❌" if dist_ok is False else "정보없음"),
                    "불일치 이유": ", ".join(issues) if issues else "",
                    "일치한 조건 수": matched,
                    "총 조건 수": total,
                })

            out = pd.DataFrame(results)
            if out.empty:
                st.warning("😢 매칭 결과가 없습니다.")
            else:
                out = out.sort_values(
                    by=["전체 조건 일치율 (%)", "나이 일치", "거리 일치"],
                    ascending=[False, True, True]
                ).reset_index(drop=True)

                st.success(f"총 {len(out)}쌍 비교 완료!")
                st.dataframe(out, use_container_width=True)
                st.download_button(
                    "📥 CSV 다운로드",
                    out.to_csv(index=False).encode("utf-8-sig"),
                    "전체조건_매칭결과.csv",
                    "text/csv"
                )

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")
else:
    st.info("TSV 붙여넣고 ➡️ 분석 시작!")
