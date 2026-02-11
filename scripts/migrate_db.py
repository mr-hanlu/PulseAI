"""
数据库迁移脚本 - 添加时间段和数据源字段
"""
import sqlite3
from pathlib import Path

def migrate_database():
    """迁移数据库，添加新字段"""
    db_path = Path(__file__).parent.parent / "data" / "weibo_data.db"
    
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return
    
    print(f"开始迁移数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查 posts 表是否有 source 字段
        cursor.execute("PRAGMA table_info(posts)")
        posts_columns = [col[1] for col in cursor.fetchall()]
        
        if 'source' not in posts_columns:
            print("添加 posts.source 字段...")
            cursor.execute("ALTER TABLE posts ADD COLUMN source TEXT DEFAULT 'weibo'")
            print("✓ posts.source 字段已添加")
        else:
            print("✓ posts.source 字段已存在")
        
        # 检查 analysis_reports 表是否有新字段
        cursor.execute("PRAGMA table_info(analysis_reports)")
        reports_columns = [col[1] for col in cursor.fetchall()]
        
        if 'time_range_start' not in reports_columns:
            print("添加 analysis_reports.time_range_start 字段...")
            cursor.execute("ALTER TABLE analysis_reports ADD COLUMN time_range_start TEXT")
            print("✓ analysis_reports.time_range_start 字段已添加")
        else:
            print("✓ analysis_reports.time_range_start 字段已存在")
        
        if 'time_range_end' not in reports_columns:
            print("添加 analysis_reports.time_range_end 字段...")
            cursor.execute("ALTER TABLE analysis_reports ADD COLUMN time_range_end TEXT")
            print("✓ analysis_reports.time_range_end 字段已添加")
        else:
            print("✓ analysis_reports.time_range_end 字段已存在")
        
        if 'source' not in reports_columns:
            print("添加 analysis_reports.source 字段...")
            cursor.execute("ALTER TABLE analysis_reports ADD COLUMN source TEXT DEFAULT 'weibo'")
            print("✓ analysis_reports.source 字段已添加")
        else:
            print("✓ analysis_reports.source 字段已存在")
        
        conn.commit()
        print("\n✅ 数据库迁移完成！")
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
