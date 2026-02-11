"""
AI热点监控系统 - Web展示界面
"""
from flask import Flask, render_template, jsonify, request
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager.storage import create_storage_manager

app = Flask(__name__)
storage = create_storage_manager()


@app.route('/')
def index():
    """首页 - 显示最新报告列表"""
    reports = storage.get_analysis_reports(limit=20)
    return render_template('index.html', reports=reports)


@app.route('/report/<int:report_id>')
def report_detail(report_id):
    """报告详情页"""
    report = storage.get_analysis_report_by_id(report_id)
    if report:
        return render_template('report.html', report=report)
    return "报告未找到", 404


@app.route('/api/reports')
def api_reports():
    """API接口 - 获取报告列表"""
    limit = request.args.get('limit', 10, type=int)
    date_key = request.args.get('date', None)
    reports = storage.get_analysis_reports(date_key=date_key, limit=limit)
    return jsonify(reports)


if __name__ == '__main__':
    print("=" * 50)
    print("AI热点监控系统 - Web界面")
    print("访问地址: http://localhost:8000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=8000)
