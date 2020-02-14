import sublime_plugin
import string
from sublime import Region


other_uppercase = "ÀÄÅČÉÊÈÎÏØŌÜÙŠŚŽŹŻ"
other_lowercase = other_uppercase.lower() + "ß∂"


def copy_regions(view):
    return list(view.sel()), view.sel()


def granular_move_pt(view, pt, by, forward=False, be_fancy=True):
    assert by in ['char', 'subword', 'word', 'bigword']

    end = 0 if not forward else view.size()

    if pt == end:
        return pt

    sign = 1 if forward else -1

    assert 0 <= pt <= view.size()
    assert 0 <= pt + sign <= view.size()

    if by == 'char':
        return pt + sign

    if by == 'bigword':
        alphanumeric = string.ascii_letters + other_lowercase + other_uppercase + '-._' + string.digits

    elif by == 'word':
        alphanumeric = string.ascii_letters + other_lowercase + other_uppercase + '-_' + string.digits

    else:
        alphanumeric = string.ascii_letters + other_lowercase + other_uppercase + '_'
        be_fancy = False

    no_newline_whitespace = string.whitespace.replace('\n', '')
    lowercase = string.ascii_lowercase + other_lowercase
    uppercase = string.ascii_uppercase + other_uppercase
    bigword_punctuation = no_newline_whitespace + string.punctuation

    g1 = view.substr(Region(pt + sign, pt))
    g2 = bigword_punctuation if by == 'bigword' else ''
    g3 = ''

    if g1 in no_newline_whitespace:
        g2 += no_newline_whitespace

    elif g1 in '=' and forward:
        g2 += '='

    elif (g1 in '=' and not forward or
          g1 in '-+<>' and forward):
        if forward and g1 == '>':
            g2 += '='
        else:
            g2 += '-+<>='

    elif g1 in alphanumeric + string.digits and by == 'subword':
        if g1.islower():
            g2 = lowercase
            if not forward:
                g3 = uppercase

        elif g1.isupper():
            g2 = uppercase
            if forward:
                g3 = lowercase

        elif g1.isdigit():
            print("YES YES YES")
            g2 = string.digits
            g3 = string.digits

        elif g1 == '_':
            g2 = '_'

        else:
            print("UNCLASSIFIED")

    elif g1 in alphanumeric:
        g2 = alphanumeric

    pt += sign

    prev = g1

    assert 0 <= pt <= view.size()
    while pt != end:
        assert 0 <= pt <= view.size()

        c = view.substr(Region(pt + sign, pt))

        if c not in g2:
            g2 = ''
            if c not in g3:
                break

        if be_fancy and (
            (c in '-_' and g1 in alphanumeric) or
            (c in string.ascii_uppercase and prev not in string.ascii_uppercase) or
            (c in string.digits and prev not in string.digits)
        ):
            g2 = g2.replace('.', '')

        if be_fancy and c == '.':
            be_fancy = False

        pt += sign

        prev = c

    return pt


def granular_move(view, edit, by, forward, extend=False, delete=False):
    assert by in ['char', 'subword', 'word', 'bigword']
    assert type(forward) == bool

    copy, regions = copy_regions(view)
    regions.clear()
    new_bs = []

    for c in copy:
        if delete and c.size() > 0:
            new_bs.append(c.b)

        else:
            new_bs.append(granular_move_pt(view, c.b, by=by, forward=forward, be_fancy=(len(copy) == 1)))

    for c, b in zip(copy, new_bs):
        regions.add(Region(c.a, b) if extend or delete else Region(b))

    if delete:
        pairs = {
            '"': '"',
            "'": "'",
            "(": ")",
            "{": "}",
            "[": "]"
        }
        for r in view.sel():
            z = view.substr(r)
            view.erase(edit, r)
            q = Region(r.begin(), r.begin() + 1)
            for symbol in reversed(z):
                if symbol in pairs and view.substr(q) == pairs[symbol]:
                    view.erase(edit, q)
                else:
                    break


def delete_by_custom_word(view, edit, by, forward):
    granular_move(view, edit, by, forward, delete=True)


def generic_line_regions_from_pt(view, pt):
    line = view.line(pt)
    line_string = view.substr(line)

    i = 0
    while i < len(line_string) and line_string[i] == ' ':
        i += 1

    if i < len(line_string):
        j = 0
        while j < len(line_string) and line_string[-1 - j] == ' ':
            j += 1
        assert i + j < len(line_string)
        assert line.begin() + i < line.end() - j
        source = Region(line.begin() + i, line.end() - j)

    else:
        j = 0
        source = None

    return line, source


def close_panel_if_requested(view, close_panel):
    if close_panel:
        file_view = view.window().active_view()
        view.window().run_command("hide_panel")

    else:
        file_view = view

    return file_view


class GranularMoveCommand(sublime_plugin.TextCommand):
    def run(self, edit, by, forward, extend=False, close_panel=False):
        file_view = close_panel_if_requested(self.view, close_panel)
        granular_move(file_view, edit, forward=forward, extend=extend, delete=False, by=by)


class GranularMoveLeftBySubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit, extend=False, close_panel=False):
        file_view = close_panel_if_requested(self.view, close_panel)
        granular_move(file_view, edit, forward=False, extend=extend, delete=False, by="subword")


class GranularMoveRightBySubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit, extend=False, close_panel=False):
        file_view = close_panel_if_requested(self.view, close_panel)
        granular_move(file_view, edit, forward=True, extend=extend, delete=False, by="subword")


class GranularMoveLeftByBigwordCommand(sublime_plugin.TextCommand):
    def run(self, edit, extend=False, close_panel=False):
        print("ur here")
        file_view = close_panel_if_requested(self.view, close_panel)
        granular_move(file_view, edit, forward=False, extend=extend, delete=False, by="bigword")


class GranularMoveRightByBigwordCommand(sublime_plugin.TextCommand):
    def run(self, edit, extend=False, close_panel=False):
        file_view = close_panel_if_requested(self.view, close_panel)
        granular_move(file_view, edit, forward=True, extend=extend, delete=False, by="bigword")


class MoveLeftByCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit, extend=False):
        granular_move(self.view, edit, by='subword', forward=False, extend=extend)


class GranularDeleteCommand(sublime_plugin.TextCommand):
    def run(self, edit, by, forward, close_panel=False):
        file_view = close_panel_if_requested(self.view, close_panel)
        granular_move(file_view, edit, forward=forward, delete=True, by=by)


class DeleteNextCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        delete_by_custom_word(self.view, edit, by='subword', forward=True)


class DeletePrevCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        delete_by_custom_word(self.view, edit, by='subword', forward=False)


class DeleteNextCustomBigwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        delete_by_custom_word(self.view, edit, by='bigword', forward=True)


class DeletePrevCustomBigwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        delete_by_custom_word(self.view, edit, by='bigword', forward=False)


class ClosePanelAndGoRightByCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        granular_move(file_view, edit, 'subword', forward=True)


class ClosePanelAndMoveHorizontalCommand(sublime_plugin.TextCommand):
    def run(self, edit, forward=True, extend=False, delete=False, by="subword"):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        granular_move(file_view, edit, forward=forward, extend=extend, delete=delete, by=by)


class ClosePanelAndGoLeftByCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        granular_move(file_view, edit, 'subword', forward=True)


class ClosePanelAndGoLeftByCustomBigwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        granular_move(file_view, edit, 'bigword', forward=False)


class ClosePanelAndGoRightByCustomWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        granular_move(file_view, edit, 'word', forward=True)


class ClosePanelAndGoLeftByCustomWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        granular_move(file_view, edit, 'word', forward=False)


class ClosePanelAndDeleteNextCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        delete_by_custom_word(file_view, edit, 'subword', True)


class ClosePanelAndDeletePrevCustomSubwordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_view = self.view.window().active_view()
        self.view.window().run_command("hide_panel")
        delete_by_custom_word(file_view, edit, 'subword', False)


# Recently added things:


class ClearSelectionsCommand(sublime_plugin.TextCommand):
    def run(self, edit, where='b'):
        regions = self.view.sel()

        if where == 'b':
            carets = [r.b for r in regions]

        elif where == 'begin':
            carets = [r.begin() for r in regions]

        elif where == 'end':
            carets = [r.end() for r in regions]

        else:
            assert False

        regions.clear()
        regions.add_all([Region(c) for c in carets])
