from vfetch.formats import group_formats, render_table, size_text
def test_group_sort_and_render():
    info = {"title":"Demo", "formats":[{"format_id":"18","vcodec":"avc1","acodec":"mp4a","height":360,"tbr":500,"ext":"mp4"},{"format_id":"137","vcodec":"avc1","acodec":"none","height":1080,"tbr":4000,"ext":"mp4"},{"format_id":"140","vcodec":"none","acodec":"mp4a","abr":128,"ext":"m4a"}]}
    groups = group_formats(info); assert groups["VIDEO ONLY"][0]["format_id"] == "137"; assert "Demo" in render_table(info, 70, True); assert size_text({"tbr":800}, 10).startswith("~")
