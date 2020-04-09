from odoo import models,fields,api,_ 
from . import amount_to_text as amount_to_text_ar
from odoo.exceptions import ValidationError

class RatificationListComplex(models.TransientModel):
	_name = 'ratification.list.complex'
	

	name = fields.Char(string='Description')
	date = fields.Date(default=fields.Date.today())

	ratification_list_ids = fields.Many2many('ratification.list')


	@api.multi
	def do_merg(self):
		ratification_list = self.env['ratification.list'].create({
			'name' : self.name,
			'date' : self.date,
			'is_complex' : True,
			})
		for rat_list in self.ratification_list_ids:

			ratification_list.partners_net_ids = [(0,0,{
				'partner_id' : rat_list.partner_id.id , 
				'net_amount' : rat_list.total_net_amount,
				'amount' : rat_list.total_amount,
				'deduction_amount' : rat_list.deduction_amount,
				})]


			rat_copy = rat_list.copy()

			self._cr.execute("update ratification_line set ratification_list_id = " + str(ratification_list.id) + " where ratification_list_id = " + str(rat_copy.id) + " ")

			self._cr.execute("update list_other_deduction set ratification_list_id = " + str(ratification_list.id) + " where ratification_list_id = " + str(rat_copy.id) + " ")

			rat_copy.unlink()

			# for line in rat_list.ratification_line_ids:
			# 	copy_line = line.copy()
			# 	copy_line.ratification_list_id = ratification_list.id 

			# for deduction_line in rat_list.other_deduction_ids:
			# 	copy_line = deduction_line.copy()
			# 	copy_line.ratification_list_id = ratification_list.id 


class RatificationList(models.Model):
	_inherit = 'ratification.list'

	partner_id = fields.Many2one('res.partner')
	is_complex = fields.Boolean(default=False)
	partners_net_ids = fields.Many2many('ratification.list.partner.net')


class RatificationList(models.Model):
	_name = 'ratification.list.partner.net'

	partner_id = fields.Many2one('res.partner')
	net_amount = fields.Float('Net Amount')
	amount =  fields.Float('Amount')
	deduction_amount =  fields.Float('Deduction Amount')


