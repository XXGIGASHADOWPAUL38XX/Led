audio_updatable_objects = []
visual_updatable_objects = []


class Updatable:
    def __init__(self):
        pass

    def c_update(self):
        pass


class AudioUpdatable(Updatable):
    def __init__(self):
        super().__init__()
        audio_updatable_objects.append(self)

    def c_update(self):
        super().c_update()


class VisualUpdatable(Updatable):
    def __init__(self):
        super().__init__()
        visual_updatable_objects.append(self)

    def c_update(self):
        super().c_update()
