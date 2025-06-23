import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const { url } = await request.json();

    if (!url) {
      return NextResponse.json(
        { error: 'URL is required' },
        { status: 400 }
      );
    }

    // Call the FastAPI backend with correct endpoint
    const response = await fetch(`${BACKEND_URL}/api/v1/crawl/single`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.detail || 'Crawling failed' },
        { status: response.status }
      );
    }

    const result = await response.json();
    
    return NextResponse.json(result);
  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json(
      { error: '서버 연결 오류가 발생했습니다. 백엔드 서버가 실행 중인지 확인해주세요.' },
      { status: 500 }
    );
  }
} 