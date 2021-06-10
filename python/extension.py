import jinja2

import apsis.actions
import apsis.lib.json
from   apsis.lib.py import tupleize
from   apsis.lib import email
from   apsis.runs import get_bind_args, template_expand

#-------------------------------------------------------------------------------

TEMPLATE = jinja2.Template("""<!doctype html>
<html>
<head>
  <title>{{ subject }}</title>
</head>
<body>
<p>
  program: <code>{{ program }}</code>
</p>
<pre>{{ output }}</pre>
</body>
</html>
""")

class EmailAction(apsis.actions.Action):
    """
    Action that sends an HTML email summarizing the run.
    """

    DEFAULT_SUBJECT = "Apsis {{ run.run_id }}: {{ run.job_id }}"

    def __init__(self, to=(), *, subject=DEFAULT_SUBJECT, from_=None, condition=None):
        self.__to = tupleize(to)
        self.__subject = jinja2.Template(str(subject))
        self.__from = from_
        self.__condition = condition


    def bind(self, run, jobs):
        condition = self.__condition.bind(run, jobs)
        return type(self)(
            self.__to, subject=__subject, from_=self.__from, condition=condition)


    @classmethod
    def from_jso(cls, jso):
        with apsis.lib.json.check_schema(jso) as pop:
            to      = pop("to", str)
            subject = pop("subject", str, default="")
            from_   = pop("from", str)
            cnd     = pop("if", apsis.actions.Condition.from_jso, default=None)
        return cls(to, from_=from_, condition=cnd)
            

    def to_jso(self):
        cnd = None if self.__condition is None else self.__condition.to_jso()
        return {
            "to"        : list(self.__to),
            "subject"   : self.__subject,
            "from"      : self.__from,
            "if"        : cnd,
        }


    async def __call__(self, apsis, run):
        if self.__condition is not None and not self.__condition(run):
            return

        program = str(run.program)
        output_meta = apsis.outputs.get_metadata(run.run_id)
        if "output" in output_meta:
            output = apsis.outputs.get_data(run.run_id, "output").decode()
        else:
            output = ""
        subject = self.__subject.render(dict(run=run))
        body = TEMPLATE.render(locals())

        smtp_cfg = apsis.cfg.get("smtp", {})
        email.send_html(
            self.__to, subject, body, from_=self.__from, smtp_cfg=smtp_cfg)



