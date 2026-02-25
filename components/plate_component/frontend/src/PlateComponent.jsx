import React from 'react'
import { StreamlitComponentBase, withStreamlitConnection } from 'streamlit-component-lib'

class PlateComponent extends StreamlitComponentBase {
  state = { x: 0, y: 0, clicked: false }

  onClick = (e) => {
    const img = e.currentTarget
    const rect = img.getBoundingClientRect()
    const scaleX = img.naturalWidth / rect.width
    const scaleY = img.naturalHeight / rect.height
    const x = Math.round((e.clientX - rect.left) * scaleX)
    const y = Math.round((e.clientY - rect.top) * scaleY)
    this.setState({ x, y, clicked: true })
  }

  onConfirm = () => {
    const { x, y } = this.state
    if (this.state.clicked && typeof Streamlit !== 'undefined') {
      Streamlit.setComponentValue({ x, y })
    }
  }

  render() {
    const args = this.props.args || {}
    const imageBase64 = args.image_base64 || ''
    const src = imageBase64.startsWith('data:') ? imageBase64 : `data:image/png;base64,${imageBase64}`

    return (
      <div style={{ display: 'inline-block', textAlign: 'center' }}>
        <img
          src={src}
          alt="ストライクゾーン"
          onClick={this.onClick}
          style={{ cursor: 'crosshair', maxWidth: '400px', height: 'auto' }}
        />
        {this.state.clicked && (
          <div style={{ marginTop: 8 }}>
            <span style={{ marginRight: 8 }}>({this.state.x}, {this.state.y})</span>
            <button type="button" onClick={this.onConfirm}>確定</button>
          </div>
        )}
      </div>
    )
  }
}

export default withStreamlitConnection(PlateComponent)
