from sqlalchemy import select
from backend.models import Memory, MemoryRevision
from backend.schemas import Fact
from backend.services.memory import delete_memory, merge_facts, resolve_memory


def test_memory_add_new_fact(app_and_client):
    _, application = app_and_client
    session_factory = application.state.sessions

    with session_factory() as db:
        owner = "user_test_memory"
        facts = [Fact(key="user.name", value="Le Van B")]

        result = merge_facts(db, owner, facts, source_message_id="msg_001")
        assert result["added"] == 1
        assert result["unchanged"] == 0
        assert result["conflicts"] == 0

        mem = db.scalar(select(Memory).where(Memory.owner == owner, Memory.key == "user.name"))
        assert mem is not None
        assert mem.value == "Le Van B"
        assert mem.version == 1
        assert mem.pending_value is None

        # Verify revision
        revisions = list(db.scalars(select(MemoryRevision).where(MemoryRevision.memory_id == mem.id)))
        assert len(revisions) == 1
        assert revisions[0].value == "Le Van B"


def test_memory_conflict_handling_and_resolution(app_and_client):
    _, application = app_and_client
    session_factory = application.state.sessions

    with session_factory() as db:
        owner = "user_conflict_test"
        # 1. Initial fact
        merge_facts(db, owner, [Fact(key="user.city", value="Hanoi")], source_message_id="msg_1")

        # 2. Conflicting fact
        conflict_res = merge_facts(
            db, owner, [Fact(key="user.city", value="Da Nang")], source_message_id="msg_2"
        )
        assert conflict_res["conflicts"] == 1
        assert conflict_res["added"] == 0

        mem = db.scalar(select(Memory).where(Memory.owner == owner, Memory.key == "user.city"))
        # Must retain original value until confirmed!
        assert mem.value == "Hanoi"
        assert mem.pending_value == "Da Nang"

        # 3. Resolve by accepting new fact
        resolve_memory(db, mem, accept=True)
        assert mem.value == "Da Nang"
        assert mem.pending_value is None
        assert mem.version == 2

        # 4. Another conflicting fact, then reject
        merge_facts(db, owner, [Fact(key="user.city", value="Ho Chi Minh")], source_message_id="msg_3")
        assert mem.pending_value == "Ho Chi Minh"

        resolve_memory(db, mem, accept=False)
        assert mem.value == "Da Nang"
        assert mem.pending_value is None


def test_delete_memory(app_and_client):
    _, application = app_and_client
    session_factory = application.state.sessions

    with session_factory() as db:
        owner = "user_delete_test"
        merge_facts(db, owner, [Fact(key="user.temp", value="Value")], source_message_id="msg_1")

        mem = db.scalar(select(Memory).where(Memory.owner == owner, Memory.key == "user.temp"))
        assert mem is not None

        mem_id = mem.id
        delete_memory(db, mem)

        re_check = db.scalar(select(Memory).where(Memory.id == mem_id))
        assert re_check is None

        revisions = list(db.scalars(select(MemoryRevision).where(MemoryRevision.memory_id == mem_id)))
        assert len(revisions) == 0
