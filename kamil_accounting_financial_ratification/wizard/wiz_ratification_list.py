from odoo import models,fields,api
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


class WizardRatificationList(models.TransientModel):
	_name ='wizard.ratification.list'

	list_type = fields.Selection([('ratification_list','Ratification List'),('ratification_list_with_items','Ratification List With Items')],default='ratification_list')
	for_bank_or_cash = fields.Selection([('bank','Bank'),('cash','For Save')],default='bank', string='For Bank or Cash')


	@api.multi
	def get_report(self):
		"""Call when button 'Print' button clicked.
		"""

		if self._context.get('list_id',False):
			list_id = self._context['list_id']
		else:
			list_id = False


		data = {
			'ids': self.ids,
			'model': self._name,
			'form': {
				'list_type':self.list_type,
				'list_id' : list_id,
				'for_bank_or_cash' : self.for_bank_or_cash,

			},
		}

		return self.env.ref('kamil_accounting_financial_ratification.ratification_list_report').report_action(self, data=data)
	

