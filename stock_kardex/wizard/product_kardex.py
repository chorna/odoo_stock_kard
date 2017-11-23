# coding: utf-8

from openerp import models, fields, api
from openerp.exceptions import UserError, ValidationError, Warning


class ProductKardex(models.TransientModel):
    _name = "stock.kardex"
    location_id = fields.Many2one('stock.location', u'Ubicación',
                                  required=True)
    product_id = fields.Many2one('product.product', 'Producto', required=True)
    date_start = fields.Date('Fecha Inicio')
    date_end = fields.Date('Fecha Fin')
    qty_start = fields.Float()
    qty_in = fields.Float()
    qty_out = fields.Float()
    qty_balance = fields.Float()
    line_ids = fields.One2many('stock.kardex.line', 'stock_kardex_id')

    @api.multi
    def create_request(self):
        stock_move = self.env['stock.move']
        stock_kardex_line = self.env['stock.kardex.line']
        product = self.env['product.product']
        cr = self.env.cr
        sc = self
        uid = self.id

        lines = self.line_ids
        ids = [line.id for line in lines]

        cr.execute("delete from stock_kardex_line where stock_kardex_id=%s" % sc.id)

        #for line in lines:
        qty_start = 0.0
        qty_balance = 0.0
        qty_in = 0.0
        qty_out = 0.0
        product_uom = False

        sql2 = "select move_id from stock_quant_move_rel qm " \
                                    "join stock_quant q on qm.quant_id = q.id "
        cr.execute(sql2)
        res = cr.fetchall()
        move_ids = []
        if res and res[0]!= None:
            for move in res:
                move_ids.append(move[0])

        ## beginning balance in 
        sql = "select sum(product_uom_qty) from stock_move where product_id=%s " \
                    "and date < '%s' and location_dest_id=%s " \
                    "and id in %s"\
                    "and state='done'" %(
                sc.product_id.id, sc.date_start, sc.location_id.id, tuple(move_ids))

        cr.execute(sql)
        res = cr.fetchone()

        if res and res[0]!= None:
            qty_start = res[0]

        ## beginning balance out
        sql = "select sum(product_uom_qty) from stock_move where product_id=%s and date < '%s' and location_id=%s and state='done'" %(
                sc.product_id.id, sc.date_start, sc.location_id.id)

        cr.execute(sql)
        res = cr.fetchone()

        if res and res[0]!= None:
            qty_start = qty_start - res[0]

        prod = product.browse([sc.product_id.id])
        #product_uom = prod.uom_id 

        data = {
            "stock_kardex_id": sc.id,
            "date": False,
            "qty_start": False,
            "qty_in": False,
            "qty_out": False,
            "qty_balance": qty_start,
            #"product_uom_id": product_uom.id,
        }
        stock_kardex_line.create(data)

        sm_ids = stock_move.search([
                    '|',
                    ('location_dest_id','=',sc.location_id.id),
                    ('location_id','=',sc.location_id.id),
                    ('product_id', 	'=' , sc.product_id.id),
                    ('date', 		'>=', sc.date_start),
                    ('date', 		'<=', sc.date_end),
                    ('state',		'=',  'done'),
                    ('id',			'in', move_ids)

            ], order='date asc')


        for sm in stock_move.browse([move.id for move in sm_ids]):
            qty_in = 0.0
            qty_out = 0.0

            #uom conversion factor
            factor = 1.0
            #if product_uom.id != sm.product_uom.id:
                #factor =  product_uom.factor / sm.product_uom.factor 

            if sm.location_dest_id == sc.location_id:	#incoming, dest = location
                qty_in = sm.product_uom_qty  * factor				
            elif sm.location_id == sc.location_id:		#outgoing, source = location
                qty_out = sm.product_uom_qty * factor

            qty_balance = qty_start + qty_in - qty_out

            name = sm.name if sm.name!=prod.display_name else ""
            partner_name = sm.partner_id.name if sm.partner_id else ""
            notes = sm.picking_id.note or ""
            po_no = sm.group_id.name if sm.group_id else ""
            origin = sm.origin or ""
            finish_product = ""

            if "MO" in origin:
                    mrp = self.env['mrp.production']
                    mo_id = mrp.search([("name","=",origin)])
                    mo = mrp.browse(mo_id)
                    finish_product = "%s:%s"%(mo[0].product_id.name,mo[0].batch_number) if mo else ""


            data = {
                "stock_kardex_id": sc.id,
                "move_id": sm.id,
                "picking_id": sm.picking_id.id,
                "date": sm.date,
                "qty_start": qty_start,
                "qty_in": qty_in,
                "qty_out": qty_out,
                "qty_balance": qty_balance,
                "product_uom_id": sm.product_uom.id,
                "name": "%s/ %s/ %s/ %s/ %s/ %s" % (name,finish_product,partner_name,po_no,notes,origin),
            }
            stock_kardex_line.create(data)
            qty_start = qty_balance

        return {
            'name': "Kardex: %s en %s" % (sc.product_id.name, sc.location_id.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'stock.kardex.line',
            'view_id': False,
            'views': [(False, 'tree')],
            'domain': [('stock_kardex_id', '=', sc.id),]
        }


class ProductKardexLine(models.TransientModel):
    _name = 'stock.kardex.line'
    stock_kardex_id = fields.Many2one('stock.kardex')
    move_id = fields.Many2one('stock.move')
    picking_id = fields.Many2one('stock.picking')
    date = fields.Date()
    qty_start = fields.Float('Cantidad Inicial')
    qty_in = fields.Float('Ingreso')
    qty_out = fields.Float('Salida')
    qty_balance = fields.Float('Saldo')
    product_uom_id = fields.Many2one('product.uom', 'UoM')
    name = fields.Char('Nombre')