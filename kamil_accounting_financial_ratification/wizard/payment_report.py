# -*- coding:utf-8 -*-
from odoo import models, fields, api


class PaymentReport(models.TransientModel):
	_name = 'wizard.payment.report'
	_description = 'Wizard Payment Report'

	date_from = fields.Date('Date From')
	date_to = fields.Date('Date To')
	budget_ids = fields.Many2many('account.analytic.account',string='Budget items')
	partner_ids = fields.Many2many('res.partner',string='Payment For')		

	def print_report(self):
		data = {
			'ids': self.ids,
			'model': self._name,
			'from': {
				'date_from': self.date_from,
				'date_to': self.date_to,
				'budget_ids': self.budget_ids.ids,
				'partner_ids':self.partner_ids.ids
			},
		}

				# use `module_name.report_id` as reference.
		# `report_action()` will call `_get_report_values()` and pass `data` automatically.
		return self.env.ref('kamil_accounting_financial_ratification.payment_report').report_action(self, data=data)

		