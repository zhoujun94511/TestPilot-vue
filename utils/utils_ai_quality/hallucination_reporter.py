#!/usr/bin/env python3
"""
幻觉检测报告模块
用于生成和展示幻觉检测结果
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from utils.utils_core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HallucinationReport:
    """幻觉检测报告"""
    report_id: str
    timestamp: str
    total_items: int
    hallucination_count: int
    hallucination_rate: float
    avg_confidence: float
    issue_summary: Dict[str, int]
    quality_score: float
    recommendations: List[str]
    detailed_results: List[Dict[str, Any]]


class HallucinationReporter:
    """幻觉检测报告生成器"""
    
    def __init__(self):
        self.reports = []
    
    def generate_report(self, 
                      detection_results: List[Dict[str, Any]], 
                      source_info: Optional[Dict[str, Any]] = None) -> HallucinationReport:
        """
        生成幻觉检测报告
        
        Args:
            detection_results: 检测结果列表
            source_info: 源信息
            
        Returns:
            幻觉检测报告
        """
        try:
            # 统计信息
            total_items = len(detection_results)
            hallucination_count = sum(1 for result in detection_results 
                                    if result.get('is_hallucination', False))
            hallucination_rate = hallucination_count / total_items if total_items > 0 else 0.0
            
            # 计算平均置信度
            confidences = [result.get('confidence', 0.0) for result in detection_results]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # 统计问题类型
            issue_summary = {}
            for result in detection_results:
                for issue in result.get('issues', []):
                    issue_type = issue.split(':')[0] if ':' in issue else '其他'
                    issue_summary[issue_type] = issue_summary.get(issue_type, 0) + 1
            
            # 计算质量得分
            quality_score = 1.0 - hallucination_rate
            
            # 生成建议
            recommendations = self._generate_recommendations(
                hallucination_rate, 
                issue_summary, 
                avg_confidence,
                source_info
            )
            
            # 创建报告
            report = HallucinationReport(
                report_id=f"hallucination_report_{int(datetime.now().timestamp())}",
                timestamp=datetime.now().isoformat(),
                total_items=total_items,
                hallucination_count=hallucination_count,
                hallucination_rate=hallucination_rate,
                avg_confidence=avg_confidence,
                issue_summary=issue_summary,
                quality_score=quality_score,
                recommendations=recommendations,
                detailed_results=detection_results
            )
            
            # 保存报告
            self.reports.append(report)
            
            logger.info(f"生成幻觉检测报告: {report.report_id}, 质量得分: {quality_score:.2f}")
            
            return report
            
        except Exception as e:
            logger.error(f"生成幻觉检测报告失败: {e}")
            raise
    
    @staticmethod
    def _generate_recommendations(hallucination_rate: float,
                                  issue_summary: Dict[str, int],
                                  avg_confidence: float,
                                  source_info: Optional[Dict[str, Any]] = None) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于幻觉率生成建议
        if hallucination_rate > 0.5:
            recommendations.append("检测到大量潜在幻觉，建议检查AI模型训练数据和提示词质量")
        elif hallucination_rate > 0.2:
            recommendations.append("检测到部分潜在幻觉，建议优化知识库内容和检索策略")
        else:
            recommendations.append("内容质量良好，建议继续保持当前配置")
        
        # 基于问题类型生成建议
        if '幻觉模式' in issue_summary:
            recommendations.append("避免使用模糊表述，提供具体的事实依据和引用")
        
        if '逻辑矛盾' in issue_summary:
            recommendations.append("检查内容逻辑一致性，避免自相矛盾的表述")
        
        if '相似度过低' in issue_summary:
            recommendations.append("确保生成内容与源文档保持一致，提高知识库质量")
        
        if '缺乏源文档' in issue_summary:
            recommendations.append("为事实性声明提供可靠的源文档支持")
        
        # 基于置信度生成建议
        if avg_confidence > 0.8:
            recommendations.append("检测置信度较高，建议人工审核相关内容")
        elif avg_confidence < 0.3:
            recommendations.append("检测置信度较低，建议优化检测算法参数")
        
        # 基于源信息生成建议
        if source_info:
            if source_info.get('source_count', 0) == 0:
                recommendations.append("缺乏源文档支持，建议提供更多参考资料")
            elif source_info.get('source_quality', 0) < 0.5:
                recommendations.append("源文档质量较低，建议使用更可靠的参考资料")
            elif source_info.get('coverage', 0) < 0.3:
                recommendations.append("源文档覆盖率不足，建议增加相关文档")
        
        return recommendations
    
    def get_report_summary(self, report_id: str) -> Optional[Dict[str, Any]]:
        """获取报告摘要"""
        for report in self.reports:
            if report.report_id == report_id:
                return {
                    'report_id': report.report_id,
                    'timestamp': report.timestamp,
                    'total_items': report.total_items,
                    'hallucination_count': report.hallucination_count,
                    'hallucination_rate': report.hallucination_rate,
                    'quality_score': report.quality_score,
                    'recommendations': report.recommendations
                }
        return None
    
    def export_report(self, report_id: str, export_format: str = 'json') -> Dict[str, Any]:
        """导出报告"""
        for report in self.reports:
            if report.report_id == report_id:
                if export_format.lower() == 'json':
                    return {
                        'success': True,
                        'format': 'json',
                        'data': asdict(report)
                    }
                elif export_format.lower() == 'html':
                    html_content = self._generate_html_report(report)
                    return {
                        'success': True,
                        'format': 'html',
                        'data': html_content
                    }
                else:
                    return {
                        'success': False,
                        'message': f'不支持的导出格式: {export_format}'
                    }
        
        return {
            'success': False,
            'message': f'未找到报告: {report_id}'
        }
    
    @staticmethod
    def _generate_html_report(report: HallucinationReport) -> str:
        """生成HTML格式报告"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>幻觉检测报告 - {report.report_id}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }}
                .quality-good {{ color: #28a745; }}
                .quality-warning {{ color: #ffc107; }}
                .quality-poor {{ color: #dc3545; }}
                .recommendations {{ background-color: #d1ecf1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .issue-summary {{ margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>幻觉检测报告</h1>
                <p><strong>报告ID:</strong> {report.report_id}</p>
                <p><strong>生成时间:</strong> {report.timestamp}</p>
            </div>
            
            <div class="summary">
                <h2>检测摘要</h2>
                <div class="metric">
                    <strong>总项目数:</strong> {report.total_items}
                </div>
                <div class="metric">
                    <strong>幻觉数量:</strong> {report.hallucination_count}
                </div>
                <div class="metric">
                    <strong>幻觉率:</strong> {report.hallucination_rate:.2%}
                </div>
                <div class="metric">
                    <strong>质量得分:</strong> 
                    <span class="{'quality-good' if report.quality_score > 0.8 else 'quality-warning' if report.quality_score > 0.6 else 'quality-poor'}">
                        {report.quality_score:.2f}
                    </span>
                </div>
            </div>
            
            <div class="issue-summary">
                <h2>问题类型统计</h2>
                <table>
                    <tr><th>问题类型</th><th>数量</th></tr>
        """
        
        for issue_type, count in report.issue_summary.items():
            html += f"<tr><td>{issue_type}</td><td>{count}</td></tr>"
        
        html += """
                </table>
            </div>
            
            <div class="recommendations">
                <h2>改进建议</h2>
                <ul>
        """
        
        for recommendation in report.recommendations:
            html += f"<li>{recommendation}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="detailed-results">
                <h2>详细结果</h2>
                <table>
                    <tr>
                        <th>项目</th>
                        <th>是否幻觉</th>
                        <th>置信度</th>
                        <th>问题</th>
                        <th>建议</th>
                    </tr>
        """
        
        for i, result in enumerate(report.detailed_results):
            is_hallucination = "是" if result.get('is_hallucination', False) else "否"
            confidence = result.get('confidence', 0.0)
            issues = "; ".join(result.get('issues', []))
            suggestions = "; ".join(result.get('suggestions', []))
            
            html += f"""
                    <tr>
                        <td>项目 {i+1}</td>
                        <td>{is_hallucination}</td>
                        <td>{confidence:.2f}</td>
                        <td>{issues}</td>
                        <td>{suggestions}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def get_all_reports(self) -> List[Dict[str, Any]]:
        """获取所有报告列表"""
        return [
            {
                'report_id': report.report_id,
                'timestamp': report.timestamp,
                'total_items': report.total_items,
                'hallucination_count': report.hallucination_count,
                'quality_score': report.quality_score
            }
            for report in self.reports
        ]


def create_hallucination_reporter() -> HallucinationReporter:
    """创建幻觉检测报告生成器"""
    return HallucinationReporter()
