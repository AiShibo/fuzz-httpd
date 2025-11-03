# structptrs.py — enumerate pointer fields inside the in-memory region of a C struct
#
# Usage:
#   (gdb) structptrs EXPR     # e.g., structptrs mystruct, structptrs '&s'
#
# Behavior:
#   - Recurses through by-value aggregates only: structs, unions, and arrays.
#   - DOES NOT dereference any pointer (no following to other objects).
#   - Enumerates pointers appearing anywhere within the object's own memory,
#     including arrays-of-pointers and pointers inside nested by-value structs.
#   - Prints each pointer field's path, static type, and current value.
#   - Finishes with a total count.
#
# Notes:
#   - Arrays: iterates full compile-time length. Flexible array members (FAMs)
#     or unknown-length arrays are skipped with a note.
#   - Unions: visits each member; may list multiple alternative layouts.
#   - Requires DWARF debug info for best results.

import gdb

def strip(t):
    try:
        return t.strip_typedefs()
    except Exception:
        return t

def is_ptr(t):
    return strip(t).code == gdb.TYPE_CODE_PTR

def is_struct(t):
    return strip(t).code == gdb.TYPE_CODE_STRUCT

def is_union(t):
    return strip(t).code == gdb.TYPE_CODE_UNION

def is_array(t):
    return strip(t).code == gdb.TYPE_CODE_ARRAY

def typename(t):
    t = strip(t)
    try:
        return t.tag or str(t)
    except Exception:
        return str(t)

def array_len(t):
    t = strip(t)
    try:
        lo, hi = t.range()
        return int(hi - lo + 1)
    except Exception:
        pass
    # Fallback by sizeof math, if available (not valid for FAMs)
    try:
        el = t.target()
        if el is not None and el.sizeof > 0 and t.sizeof > 0:
            return t.sizeof // el.sizeof
    except Exception:
        pass
    return None

def fmt_addr(v):
    try:
        return "0x{:x}".format(int(v))
    except Exception:
        return str(v)

class StructPtrEnumerator:
    def __init__(self):
        self.count = 0

    def run(self, val, root_name="<expr>"):
        self.count = 0
        self._walk_value(val, root_name)
        gdb.write(f"\nTotal pointer fields: {self.count}\n")

    def _walk_value(self, val, path):
        t = strip(val.type)

        # Pointers: report but DO NOT dereference or recurse
        if is_ptr(t):
            self._report_pointer(val, t, path)
            return

        # Arrays: iterate elements completely (if length known)
        if is_array(t):
            n = array_len(t)
            if n is None:
                gdb.write(f"{path} : <array of {typename(t.target())}> (length unknown; skipped)\n")
                return
            for i in range(n):
                try:
                    elem = val[i]
                except Exception:
                    gdb.write(f"{path}[{i}] : <inaccessible element>\n")
                    continue
                self._walk_value(elem, f"{path}[{i}]")
            return

        # Struct by value: walk fields
        if is_struct(t):
            for f in t.fields():
                # Skip artificial DWARF cruft
                try:
                    if getattr(f, "artificial", False):
                        continue
                except Exception:
                    pass

                fname = f.name if f.name else "<anon>"
                ftype = strip(f.type)
                full = f"{path}.{fname}"

                # Access field value best-effort
                try:
                    fval = val[f]
                except Exception:
                    gdb.write(f"{full} : <inaccessible>\n")
                    continue

                if is_ptr(ftype):
                    self._report_pointer(fval, ftype, full)
                elif is_array(ftype) or is_struct(ftype) or is_union(ftype):
                    self._walk_value(fval, full)
                else:
                    # scalar/non-pointer non-aggregate — ignore
                    pass
            return

        # Union by value: visit each member (layout alternatives)
        if is_union(t):
            for f in t.fields():
                fname = f.name if f.name else "<anon>"
                ftype = strip(f.type)
                full = f"{path}.{fname}"
                try:
                    fval = val[f]
                except Exception:
                    gdb.write(f"{full} : <inaccessible>\n")
                    continue

                if is_ptr(ftype):
                    self._report_pointer(fval, ftype, full)
                elif is_array(ftype) or is_struct(ftype) or is_union(ftype):
                    self._walk_value(fval, full)
                else:
                    pass
            return

        # Other scalar types: nothing to do.

    def _report_pointer(self, pval, ptype, path):
        # Just print the pointer field itself; do not dereference.
        gdb.write(f"{path} : {typename(ptype)} = {fmt_addr(pval)}\n")
        self.count += 1

class StructPtrsCommand(gdb.Command):
    """structptrs EXPR
Enumerate all pointer-typed fields inside the memory region of EXPR,
including pointers found in nested by-value structs/unions and arrays.
Does not dereference any pointer or follow to other objects.
"""

    def __init__(self):
        super(StructPtrsCommand, self).__init__(
            "structptrs", gdb.COMMAND_DATA, gdb.COMPLETE_EXPRESSION
        )

    def invoke(self, arg, from_tty):
        try:
            argv = gdb.string_to_argv(arg)
        except Exception as e:
            raise gdb.GdbError(str(e))
        if not argv:
            raise gdb.GdbError("usage: structptrs EXPR")

        expr = " ".join(argv)
        try:
            val = gdb.parse_and_eval(expr)
        except Exception as e:
            raise gdb.GdbError(f"failed to evaluate EXPR: {e}")

        enum = StructPtrEnumerator()
        enum.run(val, root_name=expr)

StructPtrsCommand()

