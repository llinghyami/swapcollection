from sqlite_utils import Database
from sqlite_utils.db import NotFoundError
import uuid
from collections import UserDict, UserList
import pickle

class SwapDict(UserDict):
    PREFIX = "swapdict_"
    PATH = "swapcollections_cache.db"
        
    def __init__(self, data={}, size_threshold: int = 1048576):
        self.db = Database(self.PATH)
        self.table = self.db["DICT"]
        self.size_threshold = size_threshold

        if not self.table.exists():
            self.table.create(
                {
                    "id": str,
                    "value": bytes,
                },
                pk="id",
            )

        super().__init__(data) # 内部で__setitem__を呼んで処理するので、ここでは何もしない

    def _setprocess(self, value):
        id = self.PREFIX + str(uuid.uuid4())
        self.table.insert({"id": id, "value": pickle.dumps(value)})
        return str(id)

    def _getprocess(self, id):
        result = self.table.get(id)
        if result:
            return pickle.loads(result["value"])
        raise NotFoundError(f"id {id} not found")

    def __setitem__(self, key, value):
        if len(pickle.dumps(value)) >= self.size_threshold:
            value = self._setprocess(value)
        return super().__setitem__(key, value)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        if type(value) == str:
            if value.startswith(self.PREFIX):
                return self._getprocess(value)
        return value

    def __repr__(self):
        self.repr_data = UserDict()
        for key, value in self.items():
            if type(value) == str:
                if value.startswith(self.PREFIX):
                    value = self._getprocess(value)
            self.repr_data[key] = value
        return repr(self.repr_data)

class SwapList(UserList):
    PREFIX = "swaplist_"
    PATH = "swapcollections_cache.db"
    
    def __init__(self, data=None, size_threshold: int = 1048576):
        self.db = Database(self.PATH)
        self.table = self.db["LIST"]
        self.size_threshold = size_threshold

        if not self.table.exists():
            self.table.create(
                {
                    "id": str,
                    "value": bytes,
                },
                pk="id",
            )

        tmp_data = []
        for i in (data or []):
            if len(pickle.dumps(i)) >= self.size_threshold:
                i = self._setprocess(i)
            tmp_data.append(i)

        super().__init__(tmp_data)

    def _setprocess(self, value):
        id = self.PREFIX + str(uuid.uuid4())
        self.table.insert({"id": id, "value": pickle.dumps(value)})
        return id

    def _getprocess(self, id):
        result = self.table.get(id)
        if result:
            return pickle.loads(result["value"])
        raise NotFoundError(f"id {id} not found")

    def __setitem__(self, i, value):
        if len(pickle.dumps(value)) >= self.size_threshold:
            value = self._setprocess(value)
        return super().__setitem__(i, value)
    
    def __getitem__(self, i):
        value = super().__getitem__(i)
        if type(value) == str:            
            if value.startswith(self.PREFIX):                
                return self._getprocess(value)
        return value
    
    def _resolve(self, value):
        """Return the original value if it's a spill ID, otherwise return as-is."""
        if isinstance(value, str) and value.startswith(self.PREFIX):
            return self._getprocess(value)
        return value

    def __contains__(self, item):
        for i in range(len(self)):
            if self[i] == item:
                return True
        return False

    def pop(self, i=-1):
        resolved = self[i]
        self.data.pop(i)
        return resolved

    def index(self, item, *args):
        start = args[0] if len(args) > 0 else 0
        stop = args[1] if len(args) > 1 else len(self)
        for i in range(start, stop):
            if self[i] == item:
                return i
        raise ValueError(f"{item!r} is not in list")

    def count(self, item):
        cnt = 0
        for i in range(len(self)):
            if self[i] == item:
                cnt += 1
        return cnt

    def remove(self, item):
        idx = self.index(item)
        del self[idx]

    def sort(self, *args, **kwds):
        resolved = [self._resolve(v) for v in self.data]
        resolved.sort(*args, **kwds)
        self.data.clear()
        for value in resolved:
            if len(pickle.dumps(value)) >= self.size_threshold:
                value = self._setprocess(value)
            self.data.append(value)

    def append(self, value):
        if len(pickle.dumps(value)) >= self.size_threshold:
            value = self._setprocess(value)
        return super().append(value)

    def extend(self, value):
        tmp_value = []
        for i in value:
            if len(pickle.dumps(i)) >= self.size_threshold:
                i = self._setprocess(i)
            tmp_value.append(i)
        return super().extend(tmp_value)

    def __repr__(self):
        self.repr_data = UserList()
        for i in self:
            if type(i) == str:
                if i.startswith(self.PREFIX):
                    i = self._getprocess(i)
            self.repr_data.append(i)
        return repr(self.repr_data)

if __name__ == "__main__":

    class TestObj:
        def __init__(self, a, b):
            self.a = a
            self.b = b
            self.c = a + b
        
        def test(self):
            return self.c

    testobj = TestObj(1, 2)

    tmp = SwapList(
        [
            "hello", 
            {"hello": "world"},
            testobj,
            1977,
        ],
        size_threshold=1,
    )

    tmp.append("hello")
    tmp.extend([{"hello": "world"}, testobj, 1977])
    tmp[2:4] = ["hello", {"hello": "world"}, testobj, 1977]
    print(tmp)


    for i in tmp:
        print(i)

    # tmp2 = SwapList(
    #     [
    #         "small",
    #         {"hello": "world"},
    #         "large",
    #         {"hello": "world", "hello": "world", "hello": "world"},
    #     ],
    #     size_threshold=1,
    # )

    # print(tmp2)
    # print(tmp2[0])
    # print(tmp2[1])
    # print(tmp2[2])    
    # print(tmp2[3])