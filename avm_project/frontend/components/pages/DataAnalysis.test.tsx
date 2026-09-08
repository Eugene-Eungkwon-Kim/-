/**
 * DataAnalysis.tsx가 dataAPI 4개 엔드포인트를 실제로 호출하고, 그 응답의
 * 3가지 형태(로딩/빈 데이터/오류)를 올바르게 렌더링하는지 검증한다.
 *
 * 이전 버전은 5,000/850/1200 같은 하드코딩 데모값을 항상 보여줘서 이런
 * 검증 자체가 불가능했다 — dataAPI를 아예 호출하지 않았기 때문이다.
 */
import { render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import DataAnalysis from './DataAnalysis'
import { dataAPI } from '@/lib/api'

jest.mock('@/lib/api', () => ({
  dataAPI: {
    getDataSummary: jest.fn(),
    getPriceDistribution: jest.fn(),
    getRegionDistribution: jest.fn(),
    getDataQuality: jest.fn(),
  },
  apiUtils: {
    handleError: (err: any) => err?.message ?? '알 수 없는 오류가 발생했습니다.',
  },
}))

const mockedDataAPI = dataAPI as jest.Mocked<typeof dataAPI>

describe('DataAnalysis', () => {
  afterEach(() => {
    jest.resetAllMocks()
  })

  it('shows an empty-state banner when comparable_sales has 0 rows', async () => {
    mockedDataAPI.getDataSummary.mockResolvedValue({
      data: { total_rows: 0, by_property_type: [], by_region: [] },
    } as any)
    mockedDataAPI.getPriceDistribution.mockResolvedValue({ data: { data: [] } } as any)
    mockedDataAPI.getRegionDistribution.mockResolvedValue({ data: { data: [] } } as any)
    mockedDataAPI.getDataQuality.mockResolvedValue({
      data: {
        total_rows: 0, missing_values: 0, missing_percentage: 0,
        outliers: 0, outlier_percentage: 0, quality_score: 0, status: 'no_data',
      },
    } as any)

    render(<DataAnalysis />)

    expect(await screen.findByText('수집된 실거래 없음')).toBeInTheDocument()
    expect(screen.getByText('총 행').nextSibling).toHaveTextContent('0')
    expect(screen.getByText('평가할 데이터 없음')).toBeInTheDocument()
  })

  it('renders real counts and property-type breakdown when data exists', async () => {
    mockedDataAPI.getDataSummary.mockResolvedValue({
      data: {
        total_rows: 4,
        by_property_type: [
          { name: '아파트', count: 2 },
          { name: '토지', count: 1 },
          { name: '상가', count: 1 },
        ],
        by_region: [{ name: '강남구', count: 2 }],
      },
    } as any)
    mockedDataAPI.getPriceDistribution.mockResolvedValue({
      data: { data: [{ range: '5-10억', count: 2 }, { range: '10-15억', count: 2 }] },
    } as any)
    mockedDataAPI.getRegionDistribution.mockResolvedValue({
      data: { data: [{ name: '강남구', value: 2 }, { name: '송파구', value: 1 }] },
    } as any)
    mockedDataAPI.getDataQuality.mockResolvedValue({
      data: {
        total_rows: 4, missing_values: 0, missing_percentage: 0,
        outliers: 0, outlier_percentage: 0, quality_score: 1.0, status: 'excellent',
      },
    } as any)

    render(<DataAnalysis />)

    await waitFor(() => expect(screen.getByText('총 행').nextSibling).toHaveTextContent('4'))
    expect(screen.queryByText('수집된 실거래 없음')).not.toBeInTheDocument()
    expect(screen.getByText('아파트 2건')).toBeInTheDocument()
    expect(screen.getByText('토지 1건')).toBeInTheDocument()
    expect(screen.getByText('상가 1건')).toBeInTheDocument()
    expect(screen.getByText('매우 우수')).toBeInTheDocument()
  })

  it('shows an error message instead of crashing when the API call fails', async () => {
    mockedDataAPI.getDataSummary.mockRejectedValue(new Error('Network Error'))
    mockedDataAPI.getPriceDistribution.mockResolvedValue({ data: { data: [] } } as any)
    mockedDataAPI.getRegionDistribution.mockResolvedValue({ data: { data: [] } } as any)
    mockedDataAPI.getDataQuality.mockResolvedValue({ data: {} } as any)

    render(<DataAnalysis />)

    expect(await screen.findByText('데이터 조회 실패')).toBeInTheDocument()
    expect(screen.getByText('Network Error')).toBeInTheDocument()
  })
})
