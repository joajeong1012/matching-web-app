import streamlit as st
import pandas as pd
from io import StringIO
from itertools import permutations
import re

# ------------------ UI ------------------
st.set_page_config(page_title="💘 레이디 매칭 분석기 4.0", layout="wide")
st.title("🌈 레이디 이어주기 매칭 분석기 4.0")
st.markdown("TSV(탭 구분) 데이터를 복사-붙여넣기 후 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요")

raw_text = st.text_area("📥 TSV 데이터 붙여넣기", height=250, placeholder="여기에 전체 응답을 탭으로 구분된 형식으로 붙여넣으세요")
start = st.button("🔍 분석 시작")

# ------------------ 헬퍼 함수 ------------------
def clean_header(cols: pd.Index) -> pd.Index:
    """줄바꿈·중복 공백 제거"""
    return (cols.str.replace(r"\s+", " ", regex=True)
                .str.replace("\n", " ")
                .str.strip())

def tokenize(val: str):
    """쉼표·슬래시·공백 기준 토큰화"""
    if pd.isna(val): 
        return []
    return [t.strip() for t in re.split(r"[,/]|\\s+", str(val)) if t.strip()]

def numeric_match(value: str, pref: str) -> bool:
    """숫자 vs 범위(~) 비교"""
    try:
        v = float(value)
    except:
        return False
    pref = str(pref).replace("이상", "0~").replace("이하", "~1000").replace(" ", "")
    if "~" in pref:
        s, e = pref.split("~")
        s = float(s) if s else 0
        e = float(e) if e else 1000
        return s <= v <= e
    try:
        return v == float(pref)
    except:
        return False

# ------------------ 실행 ------------------
if start and raw_text:
    try:
        # 1) TSV → DataFrame
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = clean_header(df.columns)

        # 2) 닉네임 컬럼 찾기
        nick_cols = [c for c in df.columns if "닉네임" in c]
        if not nick_cols:
            st.error("❌ “닉네임”이라는 단어가 포함된 컬럼을 찾지 못했습니다. 헤더 줄바꿈을 제거했는지 확인하세요.")
            st.stop()
        nick = nick_cols[0]

        # 3) 꼭 맞아야 조건 컬럼
        must_col = [c for c in df.columns if "꼭 맞아야" in c]
        must_col = must_col[0] if must_col else None

        # 4) 중복·빈 닉네임 제거
        df = (df[df[nick].notna() & (df[nick].astype(str).str.strip() != "")]
                .drop_duplicates(subset=[nick])
                .reset_index(drop=True))

        st.success(f"✅ {len(df)}명 데이터 로드 완료")
        with st.expander("🔍 정제된 데이터 확인"):
            st.dataframe(df, use_container_width=True)

        # 5) 셀프/선호 쌍 자동 탐색
        pair_map = []
        for c in df.columns:
            if "(레이디)" in c and "(상대방" not in c:
                pref = c.replace("(레이디)", "(상대방 레이디)")
                if pref in df.columns:
                    pair_map.append((c, pref))

        # 숫자형 전용 쌍 수동 지정
        numeric_pairs = [
            ("레이디 나이", "선호하는 상대방 레이디 나이"),
            ("레이디 키를 적어주she레즈 (숫자만 적어주세여자)", "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)")
        ]
        pair_map += [p for p in numeric_pairs if p[0] in df.columns and p[1] in df.columns]

        # 6) 매칭 계산
        rows = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[nick].strip(), B[nick].strip()

            # --- 필수 조건 검사 ---
            if must_col:
                must_items = tokenize(A[must_col])
                fail = False
                for m in must_items:
                    if m == "거리":
                        if "단거리" in str(A.get("희망하는 거리 조건", "")) and A.get("레이디의 거주 지역") != B.get("레이디의 거주 지역"):
                            fail = True; break
                    elif m == "성격":
                        if not any(tok in tokenize(B.get("성격 [성격(레이디)]", "")) for tok in tokenize(A.get("성격 [성격(상대방 레이디)]", ""))):
                            fail = True; break
                    # 필요하면 다른 필수 조건 추가
                if fail:
                    rows.append({"A": a_nick, "B": b_nick, "궁합": "0/0", "퍼센트": 0.0, "사유": "❌ 필수 조건 불일치"})
                    continue

            # --- 일반 조건 점수 ---
            score = 0
            total = 0
            matched = []
            for self_c, pref_c in pair_map:
                a_self, a_pref = A[self_c], A[pref_c]
                b_self, b_pref = B[self_c], B[pref_c]

                # 비교 가능 여부
                if pd.isna(a_pref) and pd.isna(b_pref):
                    continue
                total += 1

                cond_met = False
                if "나이" in self_c or "키" in self_c:  # 숫자 비교
                    cond_met = numeric_match(A[self_c], B[pref_c]) or numeric_match(B[self_c], A[pref_c])
                else:  # 토큰 교차 비교
                    cond_met = any(tok in tokenize(b_self) for tok in tokenize(a_pref)) or \
                               any(tok in tokenize(a_self) for tok in tokenize(b_pref))

                if cond_met:
                    score += 1
                    matched.append(self_c.split("(")[0].strip())

            percent = round(score / total * 100, 1) if total else 0.0
            rows.append({
                "A": a_nick, "B": b_nick,
                "궁합 점수": f"{score}/{total}",
                "퍼센트": percent,
                "일치 조건": ", ".join(matched) if matched else "-"
            })

        result_df = pd.DataFrame(rows).sort_values("퍼센트", ascending=False)

        if result_df.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.header("💘 매칭 결과")
            st.dataframe(result_df, use_container_width=True)
            st.download_button("📥 결과 CSV 다운로드",
                               result_df.to_csv(index=False).encode("utf-8-sig"),
                               file_name="lady_match_results.csv",
                               mime="text/csv")

    except Exception as e:
        st.error(f"❌ 분석 실패: {e}")

else:
    st.info("👆 TSV 데이터를 붙여넣고 ➡️ **[🔍 분석 시작]** 버튼을 눌러주세요!")
