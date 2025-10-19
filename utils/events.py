
from sqlalchemy import event
from models.image import Image
from models.community import Post
from dependencies import get_storage_manager_instance

@event.listens_for(Image, 'before_delete')
def before_delete_image_listener(mapper, connection, target):
    """Listen for the 'before_delete' event on Image objects and delete the corresponding file from storage."""
    storage_manager = get_storage_manager_instance()
    if target.url:
        storage_manager.delete(target.url)

@event.listens_for(Post, 'before_delete')
def before_delete_post_listener(mapper, connection, target):
    """Listen for the 'before_delete' event on Post objects and delete the map_image_url from storage."""
    storage_manager = get_storage_manager_instance()
    if target.map_image_url:
        storage_manager.delete(target.map_image_url)
