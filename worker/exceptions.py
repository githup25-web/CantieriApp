class WorkerError(Exception):
    pass


class EventProcessingError(WorkerError):
    pass


class EventFetchError(WorkerError):
    pass


class EventStateError(WorkerError):
    pass
