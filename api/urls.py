from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token, ObtainJSONWebToken
from .views import *
from .jwt_utils import CustomJWTSerializer

class CustomDefaultRouter(DefaultRouter):

    def __init__(self):
        super().__init__()
        self.trailing_slash = '/?'

router = CustomDefaultRouter()
router.register('country', CountryViewSet, basename='countries')
router.register('state', StateViewSet, basename='states')
router.register('city', CityViewSet, basename='cities')
router.register('user', UserViewSet, basename='users')
router.register('otp', OTPViewSet, basename='otps')
router.register('badge', BadgeViewSet, basename='badges')
router.register('userLocation', UserLocationViewSet, basename='userLocations')
router.register('provider', ProviderViewSet, basename='providers')
router.register('restaurant', RestaurantViewSet, basename='restaurants')
router.register('restaurantFile', RestaurantFileViewSet, basename='restaurantFiles')
router.register('restaurantRatingType', RestaurantRatingTypeViewSet, basename='restarantRatingTypes')
router.register('restaurantRating', RestaurantRatingViewSet, basename='restaurantRatings')
router.register('tag', TagViewSet, basename='tags')
router.register('dishTag', DishTagViewSet, basename='dishTags')
router.register('dish', DishViewSet, basename='dishes')
router.register('dishRatingType', DishRatingTypeViewSet, basename='dishRatingTypes')
router.register('dishRating', DishRatingViewSet, basename='dishRatings')
router.register('dishCollection', DishCollectionViewSet, basename='dishCollections')
router.register('post', PostViewSet, basename='posts')
router.register('postFile', PostFileViewSet, basename='postFiles')
router.register('postComment', PostCommentViewSet, basename='postComments')
router.register('activity', ActivityViewSet, basename='activities')
router.register('postActivity', PostActivityViewSet, basename='postActivities')
router.register('postCommentActivity', PostCommentActivityViewSet, basename='postCommentActivities')
router.register('feedback', FeedbackViewSet, basename='feedbacks')
router.register('dataStore', DataStoreViewSet, basename='dataStores')

urlpatterns = router.urls

urlpatterns+=[
    path(r'search/', SearchView.as_view()),
    path(r'follow/', FollowView.as_view()),
    path(r'favouriteDish/', FavouriteDishView.as_view()),
    path(r'likePost/', LikePostView.as_view()),
    path(r'likePostComment/', LikePostCommentView.as_view()),

    path(r'fileUpload/', FileUploadView.as_view()),
    path(r'fileGenerate/', FileGenerateView.as_view()),
    path(r'login/', LoginView.as_view()),
    path(r'auth/token/', ObtainJSONWebToken.as_view(serializer_class=CustomJWTSerializer)),
    path(r'auth/deleteToken/', DeleteTokenView.as_view()),
    path(r'auth/isAuthenticated/', AuthUserView.as_view()),
    path(r'auth/register/', ObtainJSONWebToken.as_view(serializer_class=CustomJWTSerializer)),
    path(r'auth/password_reset/', PasswordResetView.as_view()),
    path(r'auth/referralData/', AuthUserReferralDataView.as_view()),
]
