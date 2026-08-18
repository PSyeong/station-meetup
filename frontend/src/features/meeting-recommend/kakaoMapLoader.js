const SDK_SRC = "https://dapi.kakao.com/v2/maps/sdk.js"

let loadPromise = null

export function getKakaoJsKey() {
  return import.meta.env.VITE_KAKAO_JS_KEY || ""
}

export function loadKakaoMaps() {
  if (loadPromise) return loadPromise

  const appkey = getKakaoJsKey()
  if (!appkey) {
    const err = new Error("VITE_KAKAO_JS_KEY가 설정되지 않았습니다.")
    console.error(err.message)
    return Promise.reject(err)
  }

  if (window.kakao?.maps) {
    loadPromise = Promise.resolve(window.kakao)
    return loadPromise
  }

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script")
    script.src = `${SDK_SRC}?appkey=${appkey}&autoload=false`
    script.async = true
    script.onload = () => {
      window.kakao.maps.load(() => resolve(window.kakao))
    }
    script.onerror = (ev) => {
      reject(new Error("카카오맵 SDK 로드에 실패했습니다."))
      console.error("카카오맵 SDK script 로드 실패:", ev)
    }
    document.head.appendChild(script)
  }).catch((err) => {
    loadPromise = null
    throw err
  })

  return loadPromise
}
