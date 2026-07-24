# EP02: DXF 변환의 함정 — 374개였던 텍스트가 86개로 줄어든 걸 나중에야 발견했다

**시리즈**: DWG 표제란/BOM 추출 서비스구축 #2
**이 글을 읽고 나면**: DWG→DXF 변환이 "성공"이라고 보고해도 실제로는 데이터가 조용히 유실될 수 있다는 것, 그리고 이런 종류의 침묵하는 실패(silent failure)를 어떻게 잡아내는지 알 수 있습니다.

---

## 핵심 한 줄 요약
> `dwg2dxf`가 만든 DXF 파일을 표준 파서(ezdxf)가 못 읽어서 "minimal" 옵션으로 우회했더니, 에러 없이 성공했지만 실제로는 텍스트 엔티티 374개 중 288개와 블록 참조(INSERT) 전부가 사라져 있었다. 에러가 없다고 데이터가 온전한 게 아니다.

> **자주 묻는 질문**
> **Q. ezdxf가 왜 애초에 못 읽었나요?** → `dwg2dxf`가 만든 DXF의 OBJECTS 섹션 구조가 완전한 표준 규격이 아니었다(핸들 0번 관련 파싱 오류). LibreDWG의 DWG→DXF 변환 자체가 100% 완벽하진 않다는 뜻이다.
> **Q. "minimal" 옵션이 뭔가요?** → `dwg2dxf -m`은 `$ACADVER`, `HANDSEED`, `ENTITIES` 섹션만 남기고 나머지(특히 BLOCKS/OBJECTS)를 생략하는 옵션이다. 파싱 에러는 피하지만 그 대가로 훨씬 많은 데이터를 버린다.
> **Q. 그럼 애초에 왜 DXF로 가려고 했나요?** → ezdxf가 이미 성숙한 파이썬 DXF 라이브러리라 재사용하려 했다. 결과적으로는 DXF를 아예 경유하지 않는 게 더 안전했다.

---

## 문제 상황

LibreDWG로 DWG를 직접 다룰 수 있다는 걸 확인한 다음(EP01), 실제 데이터 추출 로직을 어떻게 짤지 고민했다. Python 생태계에는 `ezdxf`라는 성숙한 DXF 파싱 라이브러리가 있다 — 이미 많은 사람이 쓰고, 문서화가 잘 돼 있고, 엔티티 순회 API가 깔끔하다. `dwg2dxf`로 DWG를 DXF로 바꾼 다음 `ezdxf`로 읽으면 될 것 같았다.

## STEP 1: 첫 시도 — 그냥 변환

```powershell
./dwg2dxf.exe sample.dwg -o sample.dxf
```

```
Reading DWG file sample.dwg
Writing DXF file sample.dxf
exit=0
```

exit code 0, 에러 메시지 없음. 성공으로 보였다.

## STEP 2: ezdxf로 읽으려니 크래시

```python
import ezdxf
doc = ezdxf.readfile("sample.dxf")
```

```
ValueError: Invalid handle 0.
  File "...\ezdxf\sections\objects.py", line 162, in setup_object_management_tables
  File "...\ezdxf\entitydb.py", line 94, in __setitem__
```

OBJECTS 섹션의 딕셔너리 핸들 복원 단계에서 죽었다. ezdxf에는 손상된 DXF를 관대하게 읽는 `recover` 모드가 있어서 시도해봤다.

```python
from ezdxf import recover
doc, auditor = recover.readfile("sample.dxf")
```

**똑같은 에러가 똑같은 위치에서 재현됐다.** recover 모드조차 이 단계(OBJECTS 섹션 초기 로드)까지 가기 전에 죽어서, 엔티티 단위 복구 로직이 작동할 기회조차 없었다.

## STEP 3: 우회 — minimal 모드

`dwg2dxf --help`를 보니 `-m`(`--minimal`) 옵션이 있었다: "only $ACADVER, HANDSEED and ENTITIES". OBJECTS 섹션 자체를 안 만들면 그 파싱 단계를 통째로 건너뛸 수 있겠다 싶었다.

```powershell
./dwg2dxf.exe -m -y -o sample_min.dxf sample.dwg
```

이번엔 ezdxf가 정상적으로 읽었다. 엔티티도 나왔다.

```python
doc, auditor = recover.readfile("sample_min.dxf")
msp = doc.modelspace()
from collections import Counter
print(Counter(e.dxftype() for e in msp))
```

```
Counter({'MTEXT': 87, 'LINE': 55, 'LWPOLYLINE': 8, 'CIRCLE': 5, 'ARC': 3, 'SPLINE': 1})
```

MTEXT(텍스트) 87개, 표제란도 대략 나오는 것 같고, 처음엔 "됐다"고 생각했다. 실제로 표제란 필드 추출 로직까지 만들어서 잘 동작하는 것처럼 보였다.

## STEP 4: 나중에 다른 경로로 다시 확인해보니 숫자가 안 맞았다

BOM(부품표) 추출 로직을 만들던 중, 같은 파일을 `dwgread.exe -O JSON`(DXF를 거치지 않고 DWG를 직접 JSON으로 덤프하는 별도 명령)으로도 열어봤다. 그런데 엔티티 개수가 완전히 달랐다.

```python
data = run_dwgread_json(path, DWGREAD_EXE)
mtexts = [o for o in data["OBJECTS"] if o.get("entity") == "MTEXT"]
print(len(mtexts))
```

```
374
```

**DXF minimal 경로로는 87개였던 MTEXT가, DWG를 직접 JSON으로 읽으니 374개였다.** 287개, 즉 원본의 77%가 DXF 변환 과정에서 조용히 사라졌던 것이다. 게다가:

```python
inserts = [o for o in data["OBJECTS"] if o.get("entity") == "INSERT"]
print(len(inserts))
```

```
32
```

**INSERT(블록 참조) 32개는 DXF minimal 경로에서 아예 0개였다.** `-m` 옵션의 "ENTITIES만 남긴다"는 말 그대로, modelspace에 직접 놓인 텍스트만 살아남고 블록 안에 들어있는 데이터는 통째로 사라진 것이다. 이건 나중에 매우 중요한 문제로 돌아온다 — **BOM(부품표) 자체가 블록 안에 들어있었기 때문**이다(이 얘기는 EP04에서 자세히 다룬다).

## STEP 5: 왜 하필 "조용히" 사라졌나

가장 위험했던 부분은 이 유실이 **에러도 경고도 없이** 일어났다는 점이다. `dwg2dxf`는 exit code 0을 반환했고, `ezdxf.readfile()`은 예외를 던지지 않았고, 추출 로직은 정상적으로 표제란 몇 개를 뽑아냈다. "동작하는 것처럼 보이는" 상태에서 실제로는 데이터의 대부분이 없는 상태로 조용히 굴러가고 있었던 것이다.

만약 BOM 추출 로직을 만들기 전에 배포했다면, "이 도면엔 부품표가 없나 보다"라는 잘못된 결론(실제로는 있는데 못 본 것)을 실사용자에게 그대로 내보냈을 것이다.

## STEP 6: 최종 결정 — DXF를 아예 경유하지 않는다

`dwg2dxf`가 만드는 DXF 자체의 신뢰도에 의문이 생긴 이상, "minimal이 아닌 다른 옵션을 더 찾아본다"보다 **DXF 변환 단계 자체를 없애는** 게 근본적인 해결책이라고 판단했다. LibreDWG에는 `dwgread`라는 별도 도구가 있고, 이건 DWG를 DXF로 바꾸는 게 아니라 **DWG 내부 객체 구조를 그대로 JSON으로 덤프**한다 — 변환이 아니라 직역이라, 손실 가능성이 훨씬 낮다.

```python
def run_dwgread_json(dwg_path: str, dwgread_exe: str) -> dict:
    proc = subprocess.run(
        [dwgread_exe, "-O", "JSON", dwg_path],
        capture_output=True, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dwgread 실패: {proc.stderr.decode('utf-8','replace')[:500]}")
    return json.loads(proc.stdout.decode("utf-8", "replace"))
```

이후 이 프로젝트의 모든 추출 로직은 DXF/ezdxf를 완전히 배제하고 이 JSON을 직접 순회하는 방식으로 다시 짰다. ezdxf의 깔끔한 API를 포기하는 대신, 원본 데이터를 있는 그대로 신뢰할 수 있게 됐다.

---

## ✅ 완료 확인

- [ ] `dwg2dxf`(DXF 경유) 경로에서 실제 엔티티 개수와 DWG 원본 개수를 대조 검증
- [ ] exit code 0 / 예외 없음이 "데이터 무결성 보장"과 다르다는 걸 재현 사례로 확인
- [ ] DXF 미경유, `dwgread -O JSON` 직접 파싱 경로로 전환
- [ ] INSERT(블록 참조)가 minimal DXF 모드에서 사라진다는 점을 후속 BOM 개발 전에 발견

---

## 다음 편 예고
> **EP03**: DWG 원본 JSON을 직접 다루기 시작했는데, 표제란 라벨("DESIGN", "CHECK" 등)과 값을 짝짓는 알고리즘에서 예상치 못한 함정을 만났다 — 라벨이 다른 라벨을 자기 값으로 착각해버렸다.

---

## 📱 30초 쇼츠 스크립트

**제목**: "성공했다고 나왔는데 데이터의 77%가 사라져 있었다"
**길이**: 27초

| 구간 | 화면 | 자막 |
|------|------|------|
| 00:00~00:05 | exit=0 성공 로그 | "변환 성공, 에러도 없었다" |
| 00:05~00:11 | ezdxf 크래시 에러 | "그런데 표준 파서가 크래시했다" |
| 00:11~00:17 | minimal 옵션으로 우회 성공 | "우회 옵션으로 일단 넘어갔는데" |
| 00:17~00:24 | 87개 vs 374개 숫자 비교 | "나중에 보니 텍스트 77%가 사라져 있었다" |
| 00:24~00:27 | DXF 미경유 구조 | "결국 변환 자체를 없앴다" |

**해시태그**: `#DXF #DWG #데이터유실 #오픈소스버그 #ezdxf`
