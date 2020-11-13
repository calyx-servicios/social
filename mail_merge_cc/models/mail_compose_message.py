import base64
import re
import logging
from odoo import _, api, fields, models, SUPERUSER_ID, tools
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)



class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def render_payment_withholding(self, res_id):
        context = self._context
        _logger.debug('=====render_holding ======')
        attachments=[]
        _report_name='certificado_de_retencion_report_copy'
        _model='account.payment'
        payment = self.env[_model].browse(res_id)
        report=self.env['ir.actions.report'].get_report(payment)
        _logger.debug('report ID %r ', report)
        
        _logger.debug('report template %r ', report.name)
        
        report_name = (('Certificado de Retencion ' or '') + '_' + (payment.withholding_number or payment.name or '')).replace('/','')
        if report.report_type != 'aeroo':
            result, format = report.with_context(context).render_qweb_pdf([res_id])
        else:
            result, format, filename = report.with_context(context).render_aeroo(
                            [res_id], data={})

        result = base64.b64encode(result)
        ext = "." + format
        if not report_name.endswith(ext):
            report_name += ext
        attachments.append((report_name, result))
        Attachment = self.env['ir.attachment'] 
        attachment_data = {
                'name': report_name,
                'datas_fname': report_name,
                'datas': result,
                'type': 'binary'
            }
        attachment_id=Attachment.create(attachment_data).id
        return attachment_id



    @api.multi
    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        context = self._context
        _logger.debug('MailComposerMessage ====== onchange_template_id')
        res = super(MailComposeMessage, self).onchange_template_id(template_id, composition_mode, model, res_id)
        if res and 'value' in res:
            if context.get('default_model') == 'account.payment.group' and \
                     context.get('default_res_id'):
                _logger.debug('Context======>%r',context)
                values = res['value']
                payment = self.env['account.payment.group'].browse(
                    context['default_res_id'])
                payment.sent = True
                # new_attachment_ids=[]
                for pay in payment.payment_ids:
                     _logger.debug('Payment ======> %r',pay.name)
                     if pay.payment_method_code == 'withholding':
                         _logger.debug('this Payment Must be attached > %r',pay.name)
                         attachment_id=self.render_payment_withholding(pay.id)
                         values.setdefault('attachment_ids', list()).append(attachment_id)
                res['value']=values
        return res


            