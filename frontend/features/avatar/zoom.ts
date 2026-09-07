/**
 * アバター映像のズーム設定。
 *
 * ここでいうズームは「配信映像の切り抜き範囲を変える」ことで、UE のカメラは動かない。
 * `1.0` がビューポート全体。1 未満にするとエディタの UI が見えてしまうため下限にしてある。
 * カメラそのものを動かしたいときは UE 側の /set-camera を使う (README 参照)。
 */
export const ZOOM = {
  min: 1.0,
  max: 2.5,
  step: 0.1,
  default: 1.0,
} as const

export const clampZoom = (value: number) =>
  Math.min(ZOOM.max, Math.max(ZOOM.min, Number(value.toFixed(2))))
