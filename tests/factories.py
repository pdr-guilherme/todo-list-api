import secrets

import factory

from app.models.auth import Token, User
from app.models.tasks import Task
from app.schema.tasks import TaskStatus
from app.security import hash_password

_TEST_PASSWORD_HASH = hash_password("defaultpassword123")


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    name = factory.Faker("name")
    email = factory.Faker("email")
    hashed_password = factory.LazyFunction(lambda: _TEST_PASSWORD_HASH)

    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"


class TokenFactory(factory.alchemy.SQLAlchemyModelFactory):
    key = factory.LazyFunction(lambda: secrets.token_hex(40))
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Token
        sqlalchemy_session_persistence = "commit"


class TaskFactory(factory.alchemy.SQLAlchemyModelFactory):
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph", nb_sentences=2)
    status = factory.Faker("random_element", elements=TaskStatus)
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Task
        sqlalchemy_session_persistence = "commit"
