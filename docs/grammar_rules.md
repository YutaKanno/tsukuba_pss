# コーディング規則

このプロジェクトの Python コードから抽出した命名規則・文法規則。

---

## 1. 命名規則

### 変数名
- **snake_case** を使用
- 例: `rd_path`, `calc_type`, `event_frames`, `deg_bones`, `n_pitch`, `whiff_pct`
- DataFrame は `df` または `gd_df`, `xwoba_df` のように `_df` サフィックス
- 個数を表す変数は `n_` プレフィックス（例: `n_pitch`, `n_game`, `n_hit`）

### 関数名
- **snake_case** を使用
- 例: `load_rd_data()`, `calc_deg()`, `add_v_a_cols()`, `build_layout()`
- プライベート関数はアンダースコアプレフィックス（例: `_read_clientside_js()`, `_df_from_store()`, `_no_cache()`）

### 定数
- **UPPER_SNAKE_CASE** を使用
- 例: `FPS`, `DEFAULT_RD_PATH`, `DEFAULT_P_HAND`, `ANIMATION_FPS_DEFAULT`, `DATA_DIR`

### ファイル名
- **snake_case**、処理順に数字プレフィックス付き
- 例: `_1_load_rd.py`, `_2_calc_deg.py`, `_3_set_stick_lines.py`, `_5_callbacks.py`
- 共通モジュールは数字なし（例: `calc_stats.py`, `app.py`）

### DataFrame カラム名
- **snake_case**
- 座標系: `{部位}_{軸}` 形式（例: `R_shoulder_x`, `L_hip_y`）
- 派生値にサフィックス: `_adj`, `_deg`, `_v`, `_angular_v`, `_res`, `_cm`, `_kph`, `_pct`, `_diff`
- 一時計算用カラムは `temp_` プレフィックス（例: `temp_mid_shoulderline_x`, `temp_Xut_x`）

---

## 2. スペース・ホワイトスペース規則

### 丸括弧の内側にスペースを入れる

```python
# 関数呼び出し
app = Dash( __name__, serve_locally = True )
pd.read_csv( rd_path, header = None )
os.makedirs( OUTPUT_DIR, exist_ok = True )
print( f'Hello {name}' )

# 関数定義
def calc_deg( x: np.ndarray, y: np.ndarray ) -> np.ndarray:
def preprocessing( df: pd.DataFrame ) -> pd.DataFrame:

# 引数なしの場合はスペース不要
def stick_line_list() -> list:
df.copy()
```

### 角括弧の内側にスペースを入れる

```python
# インデックスアクセス
df[ 'column_name' ]
df[ f'{seg}_v_x' ]
x.shape[ 0 ]
sys.argv[ 1 ]
proba[ :, 0 ]

# リスト定義
segment_names = [ 'R_hand', 'R_wrist', 'R_elbow' ]
opts = [ { 'label': k, 'value': k } for k in deg_bones ]
```

### 波括弧の内側にスペースを入れる

```python
{ 'label': f, 'value': os.path.join( DATA_DIR, f ) }
dict( l = 45, r = 0, t = 30, b = 20 )
```

### キーワード引数の `=` の前後にスペース

```python
func( arg1, arg2, key = value )
pd.read_csv( path, encoding = 'utf-8' )
KMeans( n_clusters = 7, random_state = 42 )
model.fit( X_train, eval_set = [ ( X_test, y_test ) ] )
```

### 演算子の前後にスペース

```python
ymin = df[ f'{seg}_v_x' ].min()
n_hit = n_1BH + n_2BH + n_3BH + n_HR
zero_mask = ( x_norm == 0 ) | ( y_norm == 0 )
```

---

## 3. インデント・構造

- **4 スペース**インデント（タブは不使用）
- 関数間は **2 行** の空行
- セクション区切りに `# ------------------------------------------------------------` を使用
- 処理ブロック内部のセクション見出しに `# ========================================================` を使用
- 関連するインポートをグループ化し、グループ間に空行

---

## 4. インポート

順序: 標準ライブラリ → サードパーティ → ローカルモジュール

```python
# 標準ライブラリ
import os
import hmac

# サードパーティ
from dash import Dash
import pandas as pd
import numpy as np

# ローカルモジュール
from _5_config import FPS, ANIMATION_FPS_DEFAULT
from _2_calc_deg import calc_deg
```

---

## 5. 文字列

- **f-string** を優先使用（`.format()` や `%` は使わない）

```python
f'{segment_name}_x'
f'{calc_point}_deg'
f'{val_str} ({round( h, 1 )})'
```

---

## 6. 型ヒント

- 全ての関数シグネチャにパラメータ型と戻り値型を付ける

```python
def calc_deg(
    x: np.ndarray,
    y: np.ndarray,
    plane: str = None,
    coord_sys: np.ndarray = None,
) -> np.ndarray:

def load_rd_data( rd_path: str ) -> tuple:

def add_for_calc_cols( df: pd.DataFrame, p_hand: str, oppo_hand: str ) -> pd.DataFrame:

def build_stick_frames_data( df: pd.DataFrame, bones: list, line_color: str = 'black' ) -> list:
```

---

## 7. docstring・コメント

- docstring は `"""..."""` 形式（`'''` は使わない）
- docstring は英語を基本とする

```python
"""Compute the angle [deg] between two vectors x and y (fully vectorized)."""

"""
App constants: FPS, data directory, RD file list and dropdown options.
"""
```

- インラインコメントは **日本語** と **英語** を混在可

```python
# RD データのフレームレート（計算・data-fps-input のデフォルト）
# Mask for zero-length vectors
# plane -> zero out the irrelevant axis and set normal vector
```

---

## 8. DataFrame 操作

- コピーを取ってから操作: `df = df.copy()`
- `None` チェックを先に行う

```python
if df_json is None:
    return None
```

- リスト内包表記を活用

```python
x_cols = [ c for c in df.columns if c.endswith( '_x' ) ]
opts = [ { 'label': k, 'value': k } for k in deg_bones ]
```

---

## 9. 代入・辞書のアライメント

- 関連する代入文の `=` 位置を揃える

```python
OUTPUT_DIR    = 'output'
GAMEDATA_CSV  = 'data/ssd_vs_pitcher.csv'

NAME_LIST     = [ '渡邊俊輔', '安部晄生' ]
ENG_NAME_LIST = [ 'Watanabe', 'Abe' ]
```

- 辞書内でもキーの長さに応じてコロン位置を揃える

```python
{
    'v1_st_seg': f'{p_hand}_shoulder',
    'v1_ed_seg': f'{p_hand}_elbow',
    'coord_sys': upper_body_coord_sys,
    'plane'    : 'xy',
}
```

---

## 10. エントリポイント

```python
if __name__ == '__main__':
    app.run( debug = False )
```
