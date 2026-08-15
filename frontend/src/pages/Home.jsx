export default function Home() {
  return (
    <div className="page page--placeholder">
      <h1>만남역 추천 서비스</h1>
      <p>
        출발역을 입력하면 이동 부담이 균형 잡힌 만남역을 추천하는 서비스입니다.
        이 화면(출발역 입력 폼, 추천 결과, 장소 카드)은 담당4가 구현할 예정입니다.
      </p>
      <p className="page--placeholder__note">
        지금은 담당1이 만든 데이터 파이프라인 산출물을 검증하기 위한 임시 화면 구성입니다 — 상단의
        <strong> 지하철 노선도 </strong>
        탭에서 확인할 수 있습니다.
      </p>
    </div>
  );
}
