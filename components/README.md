# カスタムコンポーネント（ストライクゾーン・フィールド）

## ストライクゾーン (plate_component)

クリックのたびに Streamlit が rerun しないよう、座標は「確定」押下時のみ Python に返します。

### ビルド方法（任意）

JS コンポーネントを使う場合は、以下でビルドしてください。未ビルドの場合は従来の `streamlit_image_coordinates` にフォールバックします。

```bash
cd components/plate_component/frontend
npm install
npm run build
```

## フィールド (field_component)

フィールド図も同様に、将来的に JS コンポーネント化できます（選手名・ランナー表示の props を渡し、打球位置クリックを確定時のみ返す）。
