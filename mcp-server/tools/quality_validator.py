"""
크롤링 결과 품질 검증 도구
필수 콘텐츠 존재 확인, 텍스트 품질 평가, 구조적 완성도 검사
"""

import re
import logging
from typing import Dict, List, Optional, Any
from collections import Counter

logger = logging.getLogger(__name__)

class QualityValidator:
    """크롤링 결과 품질 검증"""
    
    def __init__(self):
        # 품질 검증 가중치
        self.weights = {
            "content_presence": 0.3,    # 콘텐츠 존재 여부
            "text_quality": 0.25,       # 텍스트 품질
            "structure_completeness": 0.2,  # 구조 완성도
            "metadata_richness": 0.15,   # 메타데이터 풍부도
            "extraction_accuracy": 0.1   # 추출 정확도
        }
        
        # 불량 콘텐츠 패턴
        self.noise_patterns = [
            r'(advertisement|ads|광고)',
            r'(cookie|쿠키)\s*(policy|정책)',
            r'(subscribe|구독|newsletter|뉴스레터)',
            r'(404|not found|page not found)',
            r'(error|오류|에러)',
            r'(loading|로딩|please wait)'
        ]
    
    async def validate_result(
        self, 
        extracted_data: Dict, 
        url: str,
        expected_quality: float = 70.0
    ) -> Dict:
        """
        크롤링 결과 품질 검증
        
        Args:
            extracted_data: 추출된 데이터
            url: 원본 URL
            expected_quality: 기대 품질 점수 (0-100)
            
        Returns:
            품질 검증 결과
        """
        try:
            logger.info(f"품질 검증 시작: {url}")
            
            validation_result = {
                "url": url,
                "overall_score": 0.0,
                "quality_grade": "F",
                "meets_threshold": False,
                "expected_quality": expected_quality,
                "detailed_scores": {},
                "issues": [],
                "recommendations": [],
                "extraction_confidence": 0.0,
                "retry_suggested": False
            }
            
            # 개별 품질 검사 수행
            content_score = await self._validate_content_presence(extracted_data)
            text_score = await self._validate_text_quality(extracted_data)
            structure_score = await self._validate_structure_completeness(extracted_data)
            metadata_score = await self._validate_metadata_richness(extracted_data)
            accuracy_score = await self._validate_extraction_accuracy(extracted_data, url)
            
            # 가중 평균 계산
            validation_result["detailed_scores"] = {
                "content_presence": content_score,
                "text_quality": text_score,
                "structure_completeness": structure_score,
                "metadata_richness": metadata_score,
                "extraction_accuracy": accuracy_score
            }
            
            overall_score = (
                content_score["score"] * self.weights["content_presence"] +
                text_score["score"] * self.weights["text_quality"] +
                structure_score["score"] * self.weights["structure_completeness"] +
                metadata_score["score"] * self.weights["metadata_richness"] +
                accuracy_score["score"] * self.weights["extraction_accuracy"]
            )
            
            validation_result["overall_score"] = round(overall_score, 2)
            validation_result["quality_grade"] = self._calculate_grade(overall_score)
            validation_result["meets_threshold"] = overall_score >= expected_quality
            
            # 문제점 및 권장사항 수집
            all_issues = []
            all_recommendations = []
            
            for score_data in validation_result["detailed_scores"].values():
                all_issues.extend(score_data.get("issues", []))
                all_recommendations.extend(score_data.get("recommendations", []))
            
            validation_result["issues"] = list(set(all_issues))
            validation_result["recommendations"] = list(set(all_recommendations))
            
            # 재시도 권장 여부
            validation_result["retry_suggested"] = await self._should_retry(
                validation_result, extracted_data
            )
            
            # 추출 신뢰도 계산
            validation_result["extraction_confidence"] = await self._calculate_confidence(
                validation_result, extracted_data
            )
            
            logger.info(f"품질 검증 완료: {overall_score:.1f}점 ({validation_result['quality_grade']})")
            return validation_result
            
        except Exception as e:
            logger.error(f"품질 검증 오류: {e}")
            return {
                "url": url,
                "error": str(e),
                "overall_score": 0.0,
                "quality_grade": "F",
                "meets_threshold": False,
                "retry_suggested": True
            }
    
    async def _validate_content_presence(self, data: Dict) -> Dict:
        """콘텐츠 존재 여부 검증"""
        
        score = 0
        issues = []
        recommendations = []
        
        # 필수 필드 확인
        required_fields = ["text", "title"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if not missing_fields:
            score += 40
        else:
            issues.append(f"필수 필드 누락: {', '.join(missing_fields)}")
            recommendations.append("필수 콘텐츠 추출 설정 확인 필요")
        
        # 텍스트 길이 검증
        text_content = data.get("text", "")
        text_length = len(text_content.strip())
        
        if text_length >= 1000:
            score += 30
        elif text_length >= 500:
            score += 20
        elif text_length >= 100:
            score += 10
        else:
            issues.append(f"텍스트 길이 부족: {text_length}자")
            recommendations.append("더 많은 콘텐츠 추출을 위한 설정 조정 필요")
        
        # 제목 품질 검증
        title = data.get("title", "").strip()
        if title:
            if len(title) >= 10 and len(title) <= 200:
                score += 20
            else:
                issues.append(f"제목 길이 부적절: {len(title)}자")
        else:
            issues.append("제목 없음")
        
        # 노이즈 콘텐츠 검사
        noise_detected = any(
            re.search(pattern, text_content, re.I) 
            for pattern in self.noise_patterns
        )
        
        if not noise_detected:
            score += 10
        else:
            issues.append("노이즈 콘텐츠 감지됨")
            recommendations.append("콘텐츠 필터링 강화 필요")
        
        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "details": {
                "text_length": text_length,
                "has_title": bool(title),
                "noise_detected": noise_detected
            }
        }
    
    async def _validate_text_quality(self, data: Dict) -> Dict:
        """텍스트 품질 검증"""
        
        score = 0
        issues = []
        recommendations = []
        
        text = data.get("text", "")
        
        # 문장 구조 분석
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if len(valid_sentences) >= 10:
            score += 25
        elif len(valid_sentences) >= 5:
            score += 15
        elif len(valid_sentences) >= 1:
            score += 5
        else:
            issues.append("유효한 문장 구조 부족")
        
        # 단락 구조 분석
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        
        if len(paragraphs) >= 5:
            score += 20
        elif len(paragraphs) >= 2:
            score += 10
        elif len(paragraphs) >= 1:
            score += 5
        
        # 언어 품질 검사
        words = text.split()
        unique_words = set(words)
        word_diversity = len(unique_words) / max(len(words), 1)
        
        if word_diversity > 0.5:
            score += 20
        elif word_diversity > 0.3:
            score += 10
        else:
            issues.append("어휘 다양성 부족")
            recommendations.append("더 풍부한 콘텐츠 추출 필요")
        
        # 특수문자/인코딩 문제 검사
        encoding_issues = len(re.findall(r'[^\w\s가-힣.,!?:;\-()"]', text))
        if encoding_issues > len(text) * 0.05:  # 5% 이상이면 문제
            issues.append("인코딩 문제 감지")
            recommendations.append("텍스트 인코딩 처리 개선 필요")
        else:
            score += 15
        
        # 반복 텍스트 검사
        repeated_lines = self._detect_repeated_content(text)
        if repeated_lines < 0.2:  # 20% 미만 반복이면 양호
            score += 20
        else:
            issues.append(f"반복 콘텐츠 과다: {repeated_lines:.1%}")
            recommendations.append("중복 콘텐츠 제거 로직 강화 필요")
        
        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "details": {
                "sentence_count": len(valid_sentences),
                "paragraph_count": len(paragraphs),
                "word_diversity": round(word_diversity, 3),
                "repeated_content": round(repeated_lines, 3)
            }
        }
    
    async def _validate_structure_completeness(self, data: Dict) -> Dict:
        """구조 완성도 검증"""
        
        score = 0
        issues = []
        recommendations = []
        
        # 계층구조 검증
        hierarchy = data.get("hierarchy", {})
        if hierarchy:
            if hierarchy.get("levels", 0) >= 2:
                score += 30
            elif hierarchy.get("levels", 0) >= 1:
                score += 15
            
            if hierarchy.get("quality") in ["excellent", "good"]:
                score += 20
            elif hierarchy.get("quality") == "fair":
                score += 10
        else:
            issues.append("계층구조 정보 없음")
            recommendations.append("제목 태그 추출 개선 필요")
        
        # 메타데이터 구조 검증
        metadata = data.get("metadata", {})
        essential_metadata = ["title", "description"]
        present_metadata = [key for key in essential_metadata if metadata.get(key)]
        
        if len(present_metadata) == len(essential_metadata):
            score += 25
        elif len(present_metadata) > 0:
            score += 15
        
        # 링크 구조 검증
        if data.get("links"):
            internal_links = [link for link in data["links"] if self._is_internal_link(link, data.get("url", ""))]
            external_links = [link for link in data["links"] if not self._is_internal_link(link, data.get("url", ""))]
            
            if len(internal_links) > 0 or len(external_links) > 0:
                score += 15
        
        # 이미지 정보 검증
        if data.get("images"):
            score += 10
        
        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "details": {
                "hierarchy_levels": hierarchy.get("levels", 0),
                "metadata_completeness": len(present_metadata) / len(essential_metadata),
                "has_links": bool(data.get("links")),
                "has_images": bool(data.get("images"))
            }
        }
    
    async def _validate_metadata_richness(self, data: Dict) -> Dict:
        """메타데이터 풍부도 검증"""
        
        score = 0
        issues = []
        recommendations = []
        
        metadata = data.get("metadata", {})
        
        # 기본 메타데이터 점수
        basic_fields = ["title", "description", "keywords"]
        for field in basic_fields:
            if metadata.get(field):
                score += 20
        
        # 고급 메타데이터 점수
        advanced_fields = ["author", "publish_date", "modified_date", "language"]
        for field in advanced_fields:
            if metadata.get(field):
                score += 10
        
        # 구조화된 데이터 점수
        if metadata.get("schema_org") or metadata.get("json_ld"):
            score += 20
        
        # 소셜 메타데이터 점수
        social_fields = ["og:title", "og:description", "twitter:card"]
        social_present = sum(1 for field in social_fields if metadata.get(field))
        score += min(social_present * 5, 15)
        
        # 권장사항 생성
        missing_basic = [field for field in basic_fields if not metadata.get(field)]
        if missing_basic:
            issues.append(f"기본 메타데이터 누락: {', '.join(missing_basic)}")
            recommendations.append("메타데이터 추출 규칙 개선 필요")
        
        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "details": {
                "basic_metadata_count": len([f for f in basic_fields if metadata.get(f)]),
                "advanced_metadata_count": len([f for f in advanced_fields if metadata.get(f)]),
                "has_structured_data": bool(metadata.get("schema_org") or metadata.get("json_ld")),
                "social_metadata_count": social_present
            }
        }
    
    async def _validate_extraction_accuracy(self, data: Dict, url: str) -> Dict:
        """추출 정확도 검증"""
        
        score = 70  # 기본 점수
        issues = []
        recommendations = []
        
        # URL 일치성 검증
        if data.get("url") == url:
            score += 10
        else:
            issues.append("URL 불일치")
        
        # 크롤링 엔진 정보 검증
        if data.get("metadata", {}).get("crawler_used"):
            score += 10
        
        # 처리 시간 검증 (비정상적으로 빠르거나 느린 경우)
        processing_time = data.get("metadata", {}).get("processing_time", "0s")
        time_seconds = self._parse_time_string(processing_time)
        
        if 1 <= time_seconds <= 120:  # 1초~2분 정상 범위
            score += 10
        elif time_seconds < 1:
            issues.append("처리 시간이 비정상적으로 빠름")
            recommendations.append("추출 완성도 확인 필요")
        elif time_seconds > 120:
            issues.append("처리 시간이 비정상적으로 느림")
            recommendations.append("크롤링 설정 최적화 필요")
        
        return {
            "score": min(score, 100),
            "issues": issues,
            "recommendations": recommendations,
            "details": {
                "url_matches": data.get("url") == url,
                "has_crawler_info": bool(data.get("metadata", {}).get("crawler_used")),
                "processing_time_seconds": time_seconds
            }
        }
    
    def _calculate_grade(self, score: float) -> str:
        """점수를 등급으로 변환"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "C+"
        elif score >= 65:
            return "C"
        elif score >= 60:
            return "D+"
        elif score >= 55:
            return "D"
        else:
            return "F"
    
    async def _should_retry(self, validation_result: Dict, data: Dict) -> bool:
        """재시도 권장 여부 결정"""
        
        score = validation_result["overall_score"]
        
        # 점수가 너무 낮으면 재시도
        if score < 40:
            return True
        
        # 치명적 문제가 있으면 재시도
        critical_issues = [
            "필수 필드 누락",
            "텍스트 길이 부족",
            "유효한 문장 구조 부족"
        ]
        
        for issue in validation_result.get("issues", []):
            if any(critical in issue for critical in critical_issues):
                return True
        
        # 예상 품질에 크게 못 미치면 재시도
        expected = validation_result.get("expected_quality", 70)
        if score < expected * 0.7:  # 기대치의 70% 미만
            return True
        
        return False
    
    async def _calculate_confidence(self, validation_result: Dict, data: Dict) -> float:
        """추출 신뢰도 계산"""
        
        base_confidence = validation_result["overall_score"] / 100
        
        # 보정 요소들
        adjustments = 0
        
        # 메타데이터 풍부도에 따른 보정
        metadata_score = validation_result["detailed_scores"]["metadata_richness"]["score"]
        if metadata_score > 80:
            adjustments += 0.1
        elif metadata_score < 40:
            adjustments -= 0.1
        
        # 구조 완성도에 따른 보정
        structure_score = validation_result["detailed_scores"]["structure_completeness"]["score"]
        if structure_score > 80:
            adjustments += 0.05
        elif structure_score < 40:
            adjustments -= 0.05
        
        # 이슈 수에 따른 보정
        issue_count = len(validation_result.get("issues", []))
        if issue_count == 0:
            adjustments += 0.05
        elif issue_count > 5:
            adjustments -= 0.1
        
        final_confidence = max(0.0, min(1.0, base_confidence + adjustments))
        return round(final_confidence, 3)
    
    def _detect_repeated_content(self, text: str) -> float:
        """반복 콘텐츠 비율 계산"""
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) < 2:
            return 0.0
        
        line_counts = Counter(lines)
        repeated_lines = sum(count - 1 for count in line_counts.values() if count > 1)
        
        return repeated_lines / len(lines)
    
    def _is_internal_link(self, link: str, base_url: str) -> bool:
        """내부 링크 여부 판단"""
        if not link or not base_url:
            return False
        
        if link.startswith('http'):
            from urllib.parse import urlparse
            link_domain = urlparse(link).netloc
            base_domain = urlparse(base_url).netloc
            return link_domain == base_domain
        else:
            return True  # 상대 링크는 내부 링크
    
    def _parse_time_string(self, time_str: str) -> float:
        """시간 문자열을 초 단위로 변환"""
        if not time_str:
            return 0.0
        
        # "3.2s" 형태 파싱
        match = re.search(r'(\d+\.?\d*)s', str(time_str))
        if match:
            return float(match.group(1))
        
        # "1.5 seconds" 형태 파싱
        match = re.search(r'(\d+\.?\d*)\s*seconds?', str(time_str))
        if match:
            return float(match.group(1))
        
        return 0.0 