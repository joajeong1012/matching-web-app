import pandas as pd
import re
import streamlit as st
from io import StringIO
from itertools import permutations

# ----------------- UI -----------------
st.set_page_config(page_title="💘 레이디 매칭 분석기 5.0", layout="wide")

st.title("🌈 레이디 이어주기 매칭 분석기 5.0 – 양방향 20+ 조건 평가")
st.caption("TSV 전체 붙여넣기 → [🔍 분석 시작] 클릭하면 끝!")

raw_text = st.text_area("📥 TSV 데이터를 붙여넣기", height=250)
if st.button("🔍 분석 시작") and raw_text:
    try:
        # ------- load & clean -------
        df = pd.read_csv(StringIO(raw_text), sep="\t", dtype=str, engine="python")
        df.columns = (df.columns
                      .str.replace(r"\s+", " ", regex=True)
                      .str.replace("\n", " ")
                      .str.strip())

        # 닉네임 컬럼 탐색
        nick_cols = [c for c in df.columns if "닉네임" in c]
        if not nick_cols:
            st.error("❌ 닉네임 컬럼을 찾지 못했습니다. 헤더 줄바꿈을 제거했는지 확인하세요.")
            st.stop()
        NICK = nick_cols[0]

        # 필수 조건 컬럼
        MUST = [c for c in df.columns if "꼭 맞아야" in c]
        MUST = MUST[0] if MUST else None

        df = (df[df[NICK].notna() & (df[NICK].astype(str).str.strip() != "")]  # 빈 닉 제거
                .drop_duplicates(subset=[NICK])
                .reset_index(drop=True))

        # ------- build attribute pairs -------
        self_pref_pairs = []   # [(self_col, pref_col, label)]
        for c in df.columns:
            if "(레이디)" in c and "(상대방" not in c:
                pref = c.replace("(레이디)", "(상대방 레이디)")
                if pref in df.columns:
                    lbl = c.split("[")[0].replace("(레이디)", "").strip()
                    self_pref_pairs.append((c, pref, lbl))
        # 수동 numeric 쌍 추가
        numeric_pairs = [
            ("레이디 나이", "선호하는 상대방 레이디 나이", "나이"),
            ("레이디 키를 적어주she레즈 (숫자만 적어주세여자)", "상대방 레이디 키를  적어주she레즈  (예시 : 154~, ~170)", "키")
        ]
        self_pref_pairs += [(a, b, lbl) for a, b, lbl in numeric_pairs if a in df.columns and b in df.columns]

        # 거리 조건은 별도 처리
        DIST_SELF = "레이디의 거주 지역"
        DIST_PREF = "희망하는 거리 조건"

        # ------- helper -------
        SEP = re.compile(r"[,/]|\s+")
        def tokens(x):
            return [t.strip() for t in SEP.split(str(x)) if t.strip()]

        def num_cmp(val, rng):
            try:
                v = float(val)
            except:
                return False
            rng = str(rng).replace("이상", "0~").replace("이하", "~1000").replace(" ", "")
            if "~" in rng:
                s, e = rng.split("~"); s = float(s or 0); e = float(e or 1000)
                return s <= v <= e
            try:
                return v == float(rng)
            except:
                return False

        # ------- scoring loop -------
        rows = []
        for i, j in permutations(df.index, 2):
            A, B = df.loc[i], df.loc[j]
            a_nick, b_nick = A[NICK].strip(), B[NICK].strip()
            if not a_nick or not b_nick:
                continue

            # 필수 조건 검사 (A가 요구, B가 충족?)
            if MUST:
                must_items = tokens(A[MUST])
                fail = False
                for m in must_items:
                    m = m.lower()
                    if m == "거리":
                        if "단거리" in str(A.get(DIST_PREF, "")) and A.get(DIST_SELF) != B.get(DIST_SELF):
                            fail = True; break
                    elif m == "성격":
                        if not set(tokens(B.get("성격 [성격(레이디)]", ""))).intersection(tokens(A.get("성격 [성격(상대방 레이디)]", ""))):
                            fail = True; break
                    # 더 추가 가능
                if fail:
                    rows.append({"A": a_nick, "B": b_nick, "궁합": "0/0", "퍼센트": 0.0, "일치": "❌ 필수 조건 불일치"})
                    continue

            score = 0
            total = 0
            matched = []

            for self_c, pref_c, label in self_pref_pairs:
                a_self, a_pref = A[self_c], A[pref_c]
                b_self, b_pref = B[self_c], B[pref_c]

                # 방향 1: A self ↔ B pref
                if str(b_pref).strip():
                    total += 1
                    ok = False
                    if label in ["나이", "키"]:
                        ok = num_cmp(a_self, b_pref)
                    else:
                        ok = bool(set(tokens(a_self)).intersection(tokens(b_pref)))
                    if ok:
                        score += 1
                        matched.append(f"A→{label}")

                # 방향 2: B self ↔ A pref
                if str(a_pref).strip():
                    total += 1
                    ok = False
                    if label in ["나이", "키"]:
                        ok = num_cmp(b_self, a_pref)
                    else:
                        ok = bool(set(tokens(b_self)).intersection(tokens(a_pref)))
                    if ok:
                        score += 1
                        matched.append(f"B→{label}")

            # 거리 조건 양방향
            a_dist_pref = A.get(DIST_PREF, "")
            b_dist_pref = B.get(DIST_PREF, "")
            if "단거리" in a_dist_pref or "단거리" in b_dist_pref:
                total += 2  # 각 방향 1점씩 가능
                if A[DIST_SELF] == B[DIST_SELF]:
                    score += 2
                    matched.append("거리 단거리 일치")
            else:
                # 둘 다 장거리 허용이면 일단 +2
                total += 2
                score += 2
                matched.append("거리 무관")

            percent = round(score / total * 100, 1) if total else 0.0
            rows.append({"A": a_nick, "B": b_nick, "궁합 점수": f"{score}/{total}", "퍼센트": percent, "일치 조건": ", ".join(matched)})

        out = pd.DataFrame(rows).sort_values("퍼센트", ascending=False)
        if out.empty:
            st.warning("😢 매칭 결과가 없습니다.")
        else:
            st.success(f"{len(out)}쌍 매칭 완료 ✨")
            st.dataframe(out, use_container_width=True)
            st.download_button("CSV 다운로드", out.to_csv(index=False).encode("utf-8-sig"), "lady_match_results.csv", "text/csv")

    except Exception as err:
        st.error(f"❌ 분석 실패: {err}")
else:
    st.info("TSV 전체를 붙여넣고 [🔍 분석 시작]을 눌러주세요!")
