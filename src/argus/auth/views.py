from django.contrib.auth import logout
from django.conf import settings

from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import BasicUserSerializer, UserSerializer


class ObtainNewAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        try:
            Token.objects.get(user=user).delete()
        except Token.DoesNotExist:
            pass
        token = Token.objects.create(user=user)
        return Response({"token": token.key})


class LogoutView(APIView):
    permission_classes = []

    @extend_schema(request=None, responses={"200": None})
    def post(self, request, *args, **kwargs):
        "Log out the logged in user"
        user = request.user
        if hasattr(user, "auth_token"):
            user_token = request.user.auth_token
            user_token.delete()
        # Log out from session
        logout(request)

        response = Response()
        response.delete_cookie(settings.ARGUS_TOKEN_COOKIE_NAME)
        return response


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)


class BasicUserDetail(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BasicUserSerializer
    queryset = User.objects.all()
