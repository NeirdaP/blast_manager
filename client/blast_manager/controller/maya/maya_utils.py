import maya.cmds as cmds


def get_all_audios(start, end):
    import bisect

    audios = []
    for audio in cmds.ls(type="audio"):
        audio_start = cmds.getAttr("%s.offset" % audio)
        audio_end = start + int(cmds.getAttr("%s.duration" % audio))
        audios.append((audio, audio_start, audio_end))
    audios = sorted(audios, key=lambda x: x[2])
    keys = [audio[2] for audio in audios]

    audio_i = bisect.bisect_left(keys, start)
    sounds = []
    if audio_i >= 0:
        while audio_i < len(audios) and audios[audio_i][1] < end:
            sounds.append(audios[audio_i][0])
            audio_i += 1
    return sounds


def get_frame_rate():

    time_unit = cmds.currentUnit(query=True, time=True)
    frame_rate_map = {
        "game": 15.0,
        "film": 24.0,
        "pal": 25.0,
        "ntsc": 30.0,
        "show": 48.0,
        "palf": 50.0,
        "ntscf": 60.0
    }

    # If it's a custom rate like '100fps', extract the number
    if time_unit.endswith("fps"):
        return float(time_unit.replace("fps", ""))

    return frame_rate_map.get(time_unit, 24.0)

