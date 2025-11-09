from django.urls import path

from .views import (
    create_user,
    create_users_with_list_input,
    find_pets_by_status,
    find_pets_by_tags,
    get_inventory,
    get_order_by_id,
    get_pet_by_id,
    get_user_by_name,
    login_user,
    logout_user,
    place_order,
    update_pet,
    upload_file,
)

urlpatterns = [
    path("/pet/", update_pet),
    path("/pet/findByStatus/", find_pets_by_status),
    path("/pet/findByTags/", find_pets_by_tags),
    path("/pet/<int:pet_id>/", get_pet_by_id),
    path("/pet/uploadImage/<int:pet_id>/", upload_file),
    path("/store/inventory/", get_inventory),
    path("/store/order/", place_order),
    path("/store/order/<int:order_id>/", get_order_by_id),
    path("/user/", create_user),
    path("/user/createWithList/", create_users_with_list_input),
    path("/user/login/", login_user),
    path("/user/logout/", logout_user),
    path("/user/<str:username>/", get_user_by_name),
]
