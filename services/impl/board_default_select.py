from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from sqlalchemy import func

from services.abstract.board_select import BoardSelectService
from models import Post, Comment, Report, Route
from schemas.community import PostSearchResponse


class DefaultBoardSelectService(BoardSelectService):
    def select(
        self,
        db: Session,
        user_lat: Optional[float] = None,
        user_lon: Optional[float] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> List[PostSearchResponse]:
        skip = (page - 1) * page_size

        comment_count_subquery = (
            db.query(Comment.post_id, func.count(Comment.id).label("comment_count"))
            .filter(Comment.parent_id.is_(None))
            .group_by(Comment.post_id)
            .subquery()
        )

        posts_with_comment_count = (
            db.query(Post, func.coalesce(comment_count_subquery.c.comment_count, 0))
            .options(
                selectinload(Post.images),
                selectinload(Post.report).selectinload(Report.route),
                selectinload(Post.author),
            )
            .outerjoin(comment_count_subquery, Post.id == comment_count_subquery.c.post_id)
            .filter(Post.public == True)
            .order_by(Post.created_at.desc())
            .offset(skip)
            .limit(page_size)
            .all()
        )

        response = []
        for post, count in posts_with_comment_count:
            model = PostSearchResponse.model_validate(post)
            model.comment_count = count
            if post.report and post.report.route:
                model.route_name = post.report.route.name
                model.route_id = post.report.route.id
            response.append(model)

        return response
