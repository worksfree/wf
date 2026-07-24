# EP04: BOM은 블록 안에 숨어있었다 — 그리고 두 번 검증하고도 놓친 버그

**시리즈**: DWG 표제란/BOM 추출 서비스구축 #4
**이 글을 읽고 나면**: SolidWorks가 DWG로 내보낼 때 부품표를 어떤 구조로 저장하는지, "가장 데이터가 많은 뭉치를 찾는다"는 휴리스틱이 왜 위험할 수 있는지, 그리고 두 번의 성공적인 검증 뒤에도 세 번째 실제 파일에서만 드러난 버그를 어떻게 잡았는지 알 수 있습니다.

---

## 핵심 한 줄 요약
> BOM(부품표)은 도면의 "일반 공간"이 아니라 SolidWorks가 DWG로 내보낼 때 자동 생성하는 특수 블록(`SW_TABLEANNOTATION_N`) 안에 있었다. 이걸 모르고 modelspace만 훑으면 24행짜리 부품표를 통째로 놓친다 — 그것도 "못 찾았습니다"라는 그럴듯한 메시지와 함께.

> **자주 묻는 질문**
> **Q. 왜 하필 SolidWorks 블록 이름인가요?** → 이 회사는 3D 모델은 SolidWorks로 설계하고 2D 도면은 SolidWorks의 DWG 내보내기 기능으로 만든다. SolidWorks가 표(주석 테이블)를 DWG로 내보낼 때 자동으로 이런 이름의 블록을 만드는 걸로 확인했다 — 회사 표준이 아니라 SolidWorks 자체의 동작 방식이라, 같은 툴체인을 쓰는 다른 회사 도면에서도 비슷한 패턴일 가능성이 높다.
> **Q. "두 번 검증했는데도 놓쳤다"는 게 무슨 뜻인가요?** → 실제 도면 2건으로 표제란·BOM을 전부 검증하고 "완료"라고 선언했는데, 사용자가 세 번째 실제 도면을 넣어보니 있어야 할 BOM이 "못 찾음"으로 나왔다. 원인을 파보니 처음부터 있던 설계 결함이었는데, 앞선 2건이 우연히 이 결함을 피해가는 조건이었을 뿐이었다.
> **Q. 표를 찾는 더 안전한 방법은 없나요?** → 있다. 이 편 마지막에 다루는 수정처럼, "블록 안에 있는 것만 후보로 본다"는 조건을 명시적으로 걸어야 한다 — "가장 큰 뭉치"라는 휴리스틱만으로는 부족하다.

---

## 문제 상황

표제란 추출(EP03)까지 마치고 실제 조립도(부품 12개 + 표준 부품 12개, 총 24행짜리 BOM이 있는 도면)로 테스트했다. 사람이 눈으로 보면 도면 우측 상단에 초록색 격자로 그려진 표가 명확하게 보였다 — NO/PART NAME/DESCRIPTION/수량/재질/제조사 등 9개 열, 24개 행.

## STEP 1: "MTEXT가 가장 많은 블록"이라는 첫 아이디어

표제란은 modelspace에 흩어진 개별 텍스트였지만, BOM처럼 격자로 정렬된 표는 대개 하나의 블록(반복 삽입 가능한 그룹 객체) 안에 몰려있을 거라고 추측했다. 그래서 "MTEXT 자식이 가장 많은 블록을 BOM으로 간주한다"는 규칙을 짰다.

```python
def find_bom_block(objs, min_children=20):
    by_owner = defaultdict(list)
    for m in mtexts:
        owner = _handle(m.get("ownerhandle"))
        by_owner[owner].append((x, y, text))
    best_owner = max(by_owner, key=lambda o: len(by_owner[o]))
    if len(by_owner[best_owner]) < min_children:
        return None, []
    return best_owner, by_owner[best_owner]
```

owner(소속 블록)별로 그룹을 짓고, 그 중 가장 큰 그룹을 BOM으로 채택하는 방식이다.

## STEP 2: 실제로 돌려보니 정확히 맞았다 — 블록 이름의 정체

```python
owner_counts = {426: 226, None: 86, 397: 5, ...}
```

owner 426에 MTEXT 226개가 몰려있었다(9열 × 24행 + 여유분 정도의 개수). 이 블록의 이름을 찾아보니:

```python
block_headers = [o for o in objs if o.get("entity") == "BLOCK_HEADER"]
for bh in block_headers:
    if _handle(bh.get("handle")) == 426:
        print(bh.get("name"))
```

```
SW_TABLEANNOTATION_1
```

이름 자체가 정체를 알려줬다 — **"SW"는 SolidWorks의 약자였다.** SolidWorks에서 3D로 설계한 다음 2D 도면을 DWG로 내보낼 때, 주석 테이블(부품표 등)을 이런 이름의 전용 블록으로 자동 포장해서 저장하는 것으로 확인됐다. 회사가 의도적으로 이렇게 설계한 게 아니라 SolidWorks 자체의 내보내기 규칙이었다.

이 226개 셀을 행(Y좌표)과 열(X좌표)로 재구성해서 표로 복원했다. 헤더 9개, 데이터 24행 — 화면으로 본 표와 정확히 일치했다. "완료"라고 판단하고 다음 단계로 넘어갔다.

## STEP 3: 사용자가 세 번째 실제 도면을 넣어봤다

기능이 다 완성된 뒤, 사용자가 실제 업무에 쓰는 또 다른 도면(최상위 조립도, 단품 1개짜리 BOM)을 넣어봤다. 결과는 "이 도면에서 BOM을 찾지 못했습니다"였다. 그런데 사용자가 도면 원본 스크린샷을 같이 보내왔는데, **거기엔 분명히 1행짜리 BOM이 있었다.**

## STEP 4: 재현 — owner 목록을 다시 찍어보니

```python
owner_counts = {None: 86, 426: 18, 397: 5, ...}
```

이번엔 진짜 BOM 블록(owner=426)의 MTEXT가 **18개뿐**이었다(9열 × 2행 = 18 — 헤더 1행 + 데이터 1행). 그런데 기존 코드의 `min_children=20` 기준을 밑돈다. 이것만으로도 "못 찾음" 처리가 되는데, 문제는 이게 전부가 아니었다.

`find_bom_block`의 `max()` 호출은 **owner=None(=modelspace 직속, 어떤 블록에도 안 속한 텍스트)도 후보에 포함**시키고 있었다. modelspace 직속에는 표제란·테두리 구역참조 격자·공차표·주기사항이 전부 섞여 있어서 86개나 됐다. `max()`가 고른 "가장 큰 뭉치"는 진짜 BOM(18개)이 아니라 **이 잡동사니 86개짜리 modelspace 뭉치**였다.

```python
if len(by_owner[best_owner]) < min_children:  # 86 < 20? No.
    return None, []
return best_owner, by_owner[best_owner]  # owner=None, 86개 뭉치 반환
```

86 >= 20이라 임계값 체크는 통과했고, 이 잡동사니를 표로 재구성하려고 시도했다. 결과는 당연히 의미 없는 값들("질량: 5801127.44"가 표 헤더로 잡히는 등)이었다.

## STEP 5: 왜 이게 "못 찾음"으로 나왔나 — 우연한 은폐

여기서 흥미로운 지점이 있다. 이 잘못된 값이 실제 화면에는 노출되지 않고 "못 찾음"으로 나왔다. 이유는 `find_bom_block`이 반환한 owner 값이 **파이썬의 `None` 그 자체**였고, 최종 판정 로직이 이랬기 때문이다.

```python
"bom_found": bom_owner is not None,
```

`bom_owner`가 실제로 `None`(모델스페이스를 뜻하는 값)이었으니 `bom_owner is not None`이 `False`가 되어 "못 찾음"으로 떨어진 것이다. **결과가 우연히 무해하게 나왔을 뿐, 원인은 완전히 잘못된 로직이었다.** 만약 modelspace 직속 텍스트의 owner 값이 `None`이 아니라 다른 값(가령 0)이었다면, 화면에 쓰레기 표가 그대로 노출됐을 것이다 — 지금까지 두 번의 검증에서 이 경로를 안 타본 건 순전히 운이었다.

## STEP 6: 진짜 수정 — owner=None을 후보에서 명시적으로 제외

```python
def find_bom_block(objs, min_children: int = 10):
    by_owner = defaultdict(list)
    for m in mtexts:
        owner = _handle(m.get("ownerhandle"))
        if owner is None:
            continue  # modelspace 직속 — 블록이 아니므로 BOM 후보에서 제외
        by_owner[owner].append((x, y, text))
    ...
```

동시에 `min_children`도 20 → 10으로 낮췄다. 실측으로 확인된 가장 작은 진짜 BOM(18칸)보다는 작고, BOM이 없는 도면에서 관찰된 가장 큰 가짜 블록(7칸)보다는 큰, 안전한 중간값이다.

## STEP 7: 회귀 테스트 — 기존에 맞았던 것도 여전히 맞는지

새 로직으로 기존 2건을 다시 돌렸다.

```
DWD-2524-0330-07.DWG: bom_found=False rows=0 (단품, 원래도 BOM 없음 — 유지)
DWD-2524-0340-00.DWG: bom_found=True  rows=24 (기존과 동일하게 정확)
DWD-2524-0000-00.DWG: bom_found=True  rows=1  (새로 정확히 찾음!)
```

세 파일 전부 정확했다. 특히 세 번째 파일은 실제 화면에 나온 값(NO=1, PART NAME=DWD-2524-0000-SUB, MAKER=ASS'Y)까지 정확히 일치했다.

---

## ✅ 완료 확인

- [ ] SolidWorks DWG 내보내기가 표를 `SW_TABLEANNOTATION_N` 블록으로 자동 포장한다는 것 확인
- [ ] "MTEXT가 가장 많은 owner"를 찾을 때 owner=None(modelspace 직속)을 명시적으로 제외
- [ ] `min_children` 임계값을 실측된 최소 진짜 BOM 크기와 최대 가짜 블록 크기 사이로 재조정
- [ ] 기존 검증 사례 회귀 테스트 + 신규 사례로 최종 확인
- [ ] "결과가 무해해 보인다"는 것과 "로직이 옳다"는 것을 구분하는 습관 — 우연한 은폐를 발견으로 착각하지 않기

---

## 다음 편 예고
> **EP05**: 개발하면서 계속 손으로 파일을 골라 업로드하며 테스트했다. 매번 탐색기를 열어 파일을 찾는 게 귀찮아서, 샘플을 클릭 한 번으로 바로 테스트할 수 있는 기능을 만들었다 — 그 과정에서 예상 못 한 데이터 프라이버시 문제도 하나 마주쳤다.

---

## 📱 30초 쇼츠 스크립트

**제목**: "두 번 검증했는데도 놓친 버그, 세 번째 파일에서 드러났다"
**길이**: 29초

| 구간 | 화면 | 자막 |
|------|------|------|
| 00:00~00:05 | 실제 도면 BOM 표 스크린샷 | "분명히 BOM이 있는데 '못 찾음'이라고 나왔다" |
| 00:05~00:11 | SW_TABLEANNOTATION 블록 이름 | "BOM은 SolidWorks 전용 블록 안에 있었다" |
| 00:11~00:17 | owner=None 86개 vs 진짜 BOM 18개 | "가짜 뭉치가 진짜보다 더 커서 잘못 선택됐다" |
| 00:17~00:23 | bom_owner is not None 코드 | "우연히 파이썬 None과 겹쳐서 무해하게 숨어있었다" |
| 00:23~00:29 | 3건 전부 정답 | "세 파일 모두 정확하게 고쳤다" |

**해시태그**: `#SolidWorks #DWG #BOM #버그헌팅 #소프트웨어검증`
