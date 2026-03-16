# -*- coding: UTF-8 -*-
"""
MySQL数据库管理模块
"""
import aiomysql
import json
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

class Database:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._pool = None
    
    async def init_pool(self):
        """初始化连接池"""
        if self._pool is None:
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                db=self.database,
                charset='utf8mb4',
                autocommit=True,
                minsize=1,
                maxsize=10
            )
        return self._pool
    
    @asynccontextmanager
    async def acquire(self):
        """获取连接上下文管理器"""
        if self._pool is None:
            await self.init_pool()
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                yield cur
    
    async def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
    
    # ========== 问答操作 ==========
    
    async def get_question(self, question: str, group_id: int) -> Optional[Dict]:
        """根据问题和群组ID获取问题"""
        from hoshino import logger
        logger.info(f"[eqa.db] get_question: question={question!r}, group_id={group_id}")
        async with self.acquire() as cur:
            await cur.execute(
                "SELECT * FROM eqa_questions WHERE question = %s AND group_id = %s",
                (question, group_id)
            )
            res = await cur.fetchone()
            logger.info(f"[eqa.db] get_question 结果: {res}")
            return res
    
    async def get_answers(self, question_id: int, group_id: int, user_id: int = None, is_super_admin: bool = False) -> List[Dict]:
        """获取问题的所有回答"""
        async with self.acquire() as cur:
            if is_super_admin:
                # 超级管理员可以看到所有群的回答
                sql = """
                    SELECT a.* FROM eqa_answers a
                    WHERE a.question_id = %s
                    ORDER BY a.priority DESC, a.id DESC
                """
                await cur.execute(sql, (question_id,))
            else:
                # 普通用户只能看到本群的回答
                sql = """
                    SELECT a.* FROM eqa_answers a
                    WHERE a.question_id = %s AND (a.group_id = %s OR a.is_me = 0)
                    ORDER BY a.priority DESC, a.id DESC
                """
                await cur.execute(sql, (question_id, group_id))
            
            rows = await cur.fetchall()
            from hoshino import logger
            logger.info(f"[eqa.db] get_answers 查到 {len(rows)} 条记录")
            for row in rows:
                if row.get('answer_content'):
                    row['answer_content'] = json.loads(row['answer_content'])
            return rows
    
    async def get_answer_for_user(self, question: str, group_id: int, user_id: int, 
                                   is_super_admin: bool = False, priority_self: bool = True) -> Optional[Dict]:
        """获取适合用户的回答"""
        from hoshino import logger
        question_data = await self.get_question(question, group_id)
        if not question_data:
            logger.info(f"[eqa.db] 未找到问题: {question!r} (群:{group_id})")
            return None
        
        answers = await self.get_answers(question_data['id'], group_id, user_id, is_super_admin)
        if not answers:
            logger.info(f"[eqa.db] 问题 {question_data['id']} 没有回答记录")
            return None
        
        # 优先自己的回答
        if priority_self:
            self_answers = [a for a in answers if a['user_id'] == user_id and a['is_me']]
            if self_answers:
                logger.info(f"[eqa.db] 找到用户的个人优先回答")
                return self_answers[0]
        
        # 过滤is_me的回答（如果不是自己的）
        valid_answers = []
        for ans in answers:
            if ans['is_me'] and ans['user_id'] != user_id:
                continue
            valid_answers.append(ans)
        
        if not valid_answers:
            logger.info(f"[eqa.db] 所有回答都被 is_me 过滤掉了")
            return None
        
        # 随机返回一个（这里可以改成按权重/使用次数）
        import random
        chosen = random.choice(valid_answers)
        logger.info(f"[eqa.db] 从 {len(valid_answers)} 个有效回答中随机选择了 ID: {chosen.get('id')}")
        return chosen
    
    async def add_question(self, question: str, group_id: int, is_global: bool = False) -> int:
        """添加问题，返回问题ID"""
        async with self.acquire() as cur:
            await cur.execute(
                """INSERT INTO eqa_questions (question, group_id, is_global) 
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE updated_at = NOW()""",
                (question, group_id, is_global)
            )
            # 获取ID
            await cur.execute(
                "SELECT id FROM eqa_questions WHERE question = %s AND group_id = %s",
                (question, group_id)
            )
            result = await cur.fetchone()
            return result['id']
    
    async def add_answer(self, question_id: int, user_id: int, group_id: int, 
                         is_me: bool, message: List[Dict], priority: int = 0) -> int:
        """添加回答"""
        answer_type = self._detect_answer_type(message)
        answer_content = json.dumps(message, ensure_ascii=False)
        
        async with self.acquire() as cur:
            await cur.execute(
                """INSERT INTO eqa_answers 
                   (question_id, user_id, group_id, is_me, answer_type, answer_content, priority)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (question_id, user_id, group_id, is_me, answer_type, answer_content, priority)
            )
            return cur.lastrowid
    
    async def delete_answer(self, answer_id: int) -> bool:
        """删除回答"""
        async with self.acquire() as cur:
            await cur.execute("DELETE FROM eqa_answers WHERE id = %s", (answer_id,))
            return cur.rowcount > 0
    
    async def delete_question(self, question_id: int) -> bool:
        """删除问题（级联删除回答）"""
        async with self.acquire() as cur:
            await cur.execute("DELETE FROM eqa_questions WHERE id = %s", (question_id,))
            return cur.rowcount > 0
    
    async def get_question_answers_by_user(self, group_id: int, user_id: int = None, 
                                            is_super_admin: bool = False) -> List[Dict]:
        """获取群组的问题列表"""
        async with self.acquire() as cur:
            if user_id and not is_super_admin:
                # 普通用户只看自己的
                sql = """
                    SELECT q.question, a.answer_content, a.is_me, a.user_id
                    FROM eqa_questions q
                    JOIN eqa_answers a ON q.id = a.question_id
                    WHERE q.group_id = %s AND a.user_id = %s
                    ORDER BY q.id DESC
                """
                await cur.execute(sql, (group_id, user_id))
            else:
                # 管理员看全部
                sql = """
                    SELECT q.question, a.answer_content, a.is_me, a.user_id
                    FROM eqa_questions q
                    JOIN eqa_answers a ON q.id = a.question_id
                    WHERE q.group_id = %s
                    ORDER BY q.id DESC
                """
                await cur.execute(sql, (group_id,))
            
            rows = await cur.fetchall()
            for row in rows:
                if row.get('answer_content'):
                    row['answer_content'] = json.loads(row['answer_content'])
            return rows
    
    async def find_answer_to_delete(self, question: str, group_id: int, user_id: int,
                                     is_admin: bool, is_super_admin: bool,
                                     can_delete_super: bool = False) -> Optional[int]:
        """查找要删除的回答ID"""
        question_data = await self.get_question(question, group_id)
        if not question_data:
            return None
        
        async with self.acquire() as cur:
            # 获取该问题的所有回答
            await cur.execute(
                """SELECT id, user_id, is_me FROM eqa_answers 
                   WHERE question_id = %s AND (group_id = %s OR %s)
                   ORDER BY id DESC""",
                (question_data['id'], group_id, is_super_admin)
            )
            answers = await cur.fetchall()
            
            for ans in answers:
                ans_user_id = ans['user_id']
                
                # 管理员可以删除非超级管理员的回答
                if is_admin:
                    if not can_delete_super and ans_user_id in []:  # 超级管理员列表从外面传入
                        continue
                    return ans['id']
                else:
                    # 普通用户只能删自己的
                    if ans_user_id == user_id:
                        return ans['id']
            
            return None
    
    def _detect_answer_type(self, message: List[Dict]) -> str:
        """检测回答类型"""
        has_text = False
        has_image = False
        for item in message:
            if item['type'] == 'text' and item['data'].get('text', '').strip():
                has_text = True
            elif item['type'] == 'image':
                has_image = True
        
        if has_text and has_image:
            return 'mixed'
        elif has_image:
            return 'image'
        else:
            return 'text'


# 全局数据库实例
db_instance: Optional[Database] = None

async def init_database(host: str, port: int, user: str, password: str, database: str):
    """初始化数据库"""
    global db_instance
    db_instance = Database(host, port, user, password, database)
    await db_instance.init_pool()
    return db_instance

def get_db() -> Database:
    """获取数据库实例"""
    return db_instance
