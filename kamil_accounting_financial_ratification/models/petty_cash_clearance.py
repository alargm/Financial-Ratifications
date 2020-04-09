from odoo import models,fields,api,_ 
from odoo.exceptions import ValidationError
from . import amount_to_text as amount_to_text_ar

class Clearance(models.Model):
	_name = 'ratification.petty.cash.clearance'
	_description = 'Petty Cash Clearance'
	_order = 'id desc'
	_rec_name = 'ratification_id'
	_inherit = ['mail.thread','mail.activity.mixin', 'portal.mixin']

	name = fields.Char(string='Description', related='ratification_id.the_name',track_visibility='always')
	ratification_id = fields.Many2one('ratification.ratification', string='Petty Cash',track_visibility='always')
	partner_id = fields.Many2one('res.partner', string='Employee', related='ratification_id.partner_id',track_visibility='always')
	date = fields.Date(related='ratification_id.date',track_visibility='always')
	net_amount = fields.Float(related='ratification_id.net_amount', string='Net Amount',track_visibility='always')
	net_amount_in_words = fields.Char(related='ratification_id.net_amount_in_words',track_visibility='always')
	petty_cash_amount = fields.Float(related='ratification_id.petty_cash_amount')

	
	journal_id = fields.Many2one('account.journal', string='Clearance Bank/Cash', domain=[('type','in',['bank','cash'])],track_visibility='always')
	clearance_date = fields.Date(default=fields.date.today(),track_visibility='always')

	remaining_amount = fields.Float(compute='compute_remaining_amount',track_visibility='always')
	remaining_journal_id = fields.Many2one('account.journal', string='Return Amount to Bank/Cash', domain=[('type','in',['bank','cash'])],track_visibility='always')
	remaining_account_id = fields.Many2one('account.account', string='Return Amount to Account',track_visibility='always')

	clipboard_number = fields.Char(string='Clipboard Number/39 Receipt Number',track_visibility='always')
	state = fields.Selection( [('draft','Draft'),('cleared','Cleared'),('canceled','Canceled')],default='draft' ,track_visibility='always')

	line_ids = fields.One2many('ratification.petty.cash.clearance.line','clearance_id')

	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id,track_visibility='always')
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)


	



	@api.multi
	@api.onchange('ratification_id')
	def onchange_ratification(self):
		for record in self:
			if record.ratification_id:
				for payment in self.env['ratification.payment'].search([('ratification_id','=',record.ratification_id.id)]):
					record.journal_id = payment.journal_id

	@api.multi
	@api.depends('line_ids')
	def compute_remaining_amount(self):
		for record in self:
			lines_amount = 0
			for line in record.line_ids:
				lines_amount = lines_amount + line.amount
			# if lines_amount > record.net_amount:
			# 	raise ValidationError(_('Details Can not be Bigger than Petty Cash Amount'))
			if lines_amount < record.net_amount:
				record.remaining_amount = record.petty_cash_amount - lines_amount

	@api.multi
	def show_journal_moves(self):
		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'tree,form',
			'res_model' : 'account.move',
			'domain' : [('petty_cash_clearance_id','=', self.id )],
		}


	@api.multi
	def show_bank_cash_money_supply(self):
		account_id = False
		for line in self.ratification_id.line_ids:
			if line.ratification_type == 'petty_cash':
				account_id = line.account_id.id

		return {
			'type' : 'ir.actions.act_window',
			'view_mode' : 'tree,form',
			'res_model' : 'money.supply',
			'domain' : [('petty_cash_clearance_id','=', self.id )],
			'context' : {'default_petty_cash_clearance_id': self.id, 
					'default_amount' : self.remaining_amount,
					'default_name' : self.ratification_id.name,
					'default_partner_id' : self.partner_id.id,
					'default_account_id' : account_id,
					}
		}



	



	@api.multi
	def do_cancel(self):
		for move in self.env['account.move'].search([('petty_cash_clearance_id','=',self.id)]):
			move.button_cancel()
			move.unlink()
			self.ratification_id.is_petty_cash_cleared = False
		self.state = 'canceled'


	@api.multi
	def do_clear(self):
		for record in self:
			# if len(record.line_ids) < 1:
			# 	raise ValidationError(_('Please Insert Petty cash Details'))


			lines_amount = 0
			lines_net_amount = 0
			for line in record.line_ids:
				lines_amount = lines_amount + line.amount
				lines_net_amount = lines_net_amount + line.net_amount
			if lines_amount > record.net_amount:
				raise ValidationError(_('Details Can not be Bigger than Petty Cash Amount'))
		

			for line in record.line_ids:
				if line.analytic_account_id:
					self.env['crossovered.budget'].budget_operations(do_just_check=True, do_reserve=False, do_actual=False, budget_item=line.analytic_account_id, account=line.account_id,amount=line.amount,date=record.date)


			petty_cash_account = False
			for ratification_line in record.ratification_id.line_ids:
				if ratification_line.ratification_type == 'petty_cash':
					petty_cash_account = ratification_line.account_id

			if not petty_cash_account:
				raise ValidationError(_('Please Make Sure that Petty Cash Type is exists in the Ratification'))

			move_id = self.env['account.move'].create({
				'name' : record.name,
				'date' : record.date,
				'journal_id': record.journal_id.id,
				'company_id' : record.branch_id.id,
				'petty_cash_clearance_id' : record.id,
				})

			move_lines = []
			move_lines.append((0,0,{
				'account_id': petty_cash_account.id ,
				'partner_id' : record.partner_id.id ,
				'name': record.name ,
				'credit' : lines_net_amount ,
				'debit' : 0 ,
				'move_id' : move_id.id,
				}) )

			if record.remaining_amount > 0:
				move_lines.append((0,0,{
					'account_id': petty_cash_account.id,
					'partner_id' : record.partner_id.id ,
					'name': record.name ,
					'credit' : record.remaining_amount ,
					'debit' : 0 ,
					'move_id' : move_id.id,
					}) )

				move_lines.append((0,0,{
					'account_id': record.remaining_journal_id.default_debit_account_id.id,
					'partner_id' : record.partner_id.id ,
					'name': record.name ,
					'debit' : record.remaining_amount ,
					'credit' : 0 ,
					'move_id' : move_id.id,
					}) )
				

			for line in record.line_ids:
				
				for tax in line.deduction_ids:
					tax_amount = 0
					if tax.amount_type == 'fixed':
						tax_amount = tax.amount
					if tax.amount_type == 'percent':
						tax_amount = (tax.amount * line.amount / 100)
					move_lines.append((0,0,{
						'account_id': tax.account_id.id ,
						'name': tax.name ,
						'credit' : tax_amount,
						'debit' : 0 ,
						'move_id' : move_id.id,
						}) )

				move_lines.append((0,0,{
					'account_id': line.account_id.id ,
					'partner_id' : record.partner_id.id ,
					'name': record.name ,
					'credit' : 0 ,
					'debit' : line.amount ,
					'analytic_account_id' :line.analytic_account_id.id,
					'analytic_tag_ids' : [(6,0, line.analytic_tag_ids._ids )],
					'cost_center_id' : line.cost_center_id.id,
					'move_id' : move_id.id,
					}))

			move_id.line_ids = move_lines
			move_id.post()
			record.state = 'cleared'
			record.ratification_id.is_petty_cash_cleared = True


class ClearanceLine(models.Model):
	_name = 'ratification.petty.cash.clearance.line'

	name = fields.Char(string='Description')
	analytic_account_id = fields.Many2one('account.analytic.account',string='Budget Item')
	account_id = fields.Many2one('account.account', string='Account')
	cost_center_id = fields.Many2one('kamil.account.cost.center', string='Cost Center')
	analytic_tag_ids = fields.Many2many('account.analytic.tag',string='Analytic Tags')
	amount = fields.Float()
	clearance_id = fields.Many2one('ratification.petty.cash.clearance')
	branch_id = fields.Many2one('res.company', string='Branch',default= lambda self:self.env.user.company_id.id,track_visibility='always')

	deduction_ids = fields.Many2many('account.tax', string='Deductions')

	deduction_amount = fields.Float(compute='compute_deduction_amount')
	net_amount = fields.Float(compute='compute_deduction_amount')
	company_id = fields.Many2one('res.company', default= lambda self:self.env.user.company_id.id)
	


	@api.multi
	@api.depends('deduction_ids','amount')
	def compute_deduction_amount(self):
		for record in self:
			tax_amount = 0
			for tax in record.deduction_ids:
				if tax.amount_type == 'fixed':
					tax_amount = tax_amount + tax.amount
				if tax.amount_type == 'percent':
					tax_amount = tax_amount + (tax.amount * record.amount / 100)
			record.deduction_amount = tax_amount
			record.net_amount = record.amount - record.deduction_amount

	
	@api.multi
	@api.onchange('account_id')
	def onchange_account_id(self):
		if self.account_id:
			self.analytic_account_id = self.account_id.parent_budget_item_id 


class AccountMove(models.Model):
	_inherit = 'account.move'
	
	petty_cash_clearance_id = fields.Many2one('ratification.petty.cash.clearance')

class Ratification(models.Model):
	_inherit = 'ratification.ratification'

	is_petty_cash_cleared = fields.Boolean(default=False)


class MoneySupply(models.Model):
	_inherit = 'money.supply'

	petty_cash_clearance_id = fields.Many2one('ratification.petty.cash.clearance')