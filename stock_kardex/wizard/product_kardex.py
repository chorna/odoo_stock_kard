# coding: utf-8

from openerp import models, fields, api


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
    def create_request(self, context=None):
        stock_move = self.env['stock.move']
        stock_kardex_line = self.env['stock.kardex.line']
        product = self.env['product.product']
        cr = self.env.cr

        qty_start = 0.0
        price_start = 0.0
        total_price_start = 0.0
        qty_balance = 0.0
        price_balance = 0.0
        total_price_balance = 0.0
        qty_in = 0.0
        price_in = 0.0
        total_price_in = 0.0
        qty_out = 0.0
        price_out = 0.0
        total_price_out = 0.0
        product_uom = False

        sql2 = """
            SELECT move_id 
            FROM stock_quant_move_rel qm
            JOIN stock_quant q on qm.quant_id = q.id
            """
        cr.execute(sql2)
        res = cr.fetchall()
        move_ids = []
        if res and res[0]!= None:
            for move in res:
                move_ids.append(move[0])

        ## beginning balance in 
        sql = """
            SELECT SUM(product_uom_qty), AVG(price_unit)
            FROM stock_move where product_id=%s
                AND date < '%s'
                AND location_dest_id=%s
                AND id in %s
                AND state='done'
            """ % (
                self.product_id.id,
                self.date_start,
                self.location_id.id,
                tuple(move_ids)
            )

        cr.execute(sql)
        res = cr.fetchone()

        if res and res[0]!= None:
            qty_start = res[0]
            price_start = res[1]
            total_price_start = qty_start * price_start

        ## beginning balance out
        sql = """
            SELECT SUM(product_uom_qty), AVG(price_unit)
            FROM stock_move
            WHERE product_id=%s
                AND date < '%s'
                AND location_id=%s
                AND state='done'
            """ % (
                self.product_id.id,
                self.date_start,
                self.location_id.id
            )

        cr.execute(sql)
        res = cr.fetchone()

        if res and res[0] != None:
            qty_start -= res[0]
            price_start -= res[1]
            total_price_start = qty_start * price_start

        prod = product.browse([self.product_id.id])
        #product_uom = prod.uom_id 

        data = {
            "stock_kardex_id": self.id,
            "date": False,
            "qty_start": False,
            "qty_in": False,
            "qty_out": False,
            "qty_balance": qty_start,
            "price_balance": price_start,
            "total_price_balance": total_price_start,
            #"product_uom_id": product_uom.id,
        }
        stock_kardex_line.create(data)

        sm_ids = stock_move.search([
                    '|',
                    ('location_dest_id','=',self.location_id.id),
                    ('location_id','=',self.location_id.id),
                    ('product_id', 	'=' , self.product_id.id),
                    ('date', 		'>=', self.date_start),
                    ('date', 		'<=', self.date_end),
                    ('state',		'=',  'done'),
                    ('id',			'in', move_ids)

            ], order='date asc')


        for sm in stock_move.browse([move.id for move in sm_ids]):
            qty_in = 0.0
            price_in = 0.0
            total_price_in = 0.0
            qty_out = 0.0
            price_out = 0.0
            total_price_out = 0.0

            #uom conversion factor
            factor = 1.0
            #if product_uom.id != sm.product_uom.id:
                #factor =  product_uom.factor / sm.product_uom.factor 

            if sm.location_dest_id == self.location_id:	#incoming, dest = location
                qty_in = sm.product_uom_qty  * factor
                price_in = sm.price_unit
                qty_balance = qty_start + qty_in
                total_price_in = qty_in * price_in
                price_balance = (total_price_start+total_price_in) / qty_balance

            elif sm.location_id == self.location_id:		#outgoing, source = location
                qty_out = sm.product_uom_qty * factor
                price_out = sm.price_unit
                qty_balance = qty_start - qty_out
                price_balance = price_start
                total_price_out = qty_out * price_out
            total_price_balance = qty_balance * price_balance

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
                    finish_product = "%s:%s" % (mo[0].product_id.name,
                                                mo[0].batch_number) if mo else ""

            data = {
                "stock_kardex_id": self.id,
                "move_id": sm.id,
                "picking_id": sm.picking_id.id,
                "date": sm.date,
                "qty_start": qty_start,
                "price_start": price_start,
                "total_price_start": total_price_start,
                "qty_in": qty_in,
                "price_in": price_in,
                "total_price_in": total_price_in,
                "qty_out": qty_out,
                "price_out": price_out,
                "total_price_out": total_price_out,
                "qty_balance": qty_balance,
                "price_balance": price_balance,
                "total_price_balance": total_price_balance,
                "product_uom_id": sm.product_uom.id,
                "name": "%s/ %s/ %s/ %s/ %s/ %s" % (name,
                                                    finish_product,
                                                    partner_name,
                                                    po_no,
                                                    notes,
                                                    origin),
            }
            stock_kardex_line.create(data)
            qty_start = qty_balance
            price_start = price_balance
            total_price_start = total_price_balance

        _view_id = False
        if 'kardex_stock' in context.keys():
            if not context['kardex_stock']:
                _ref, _view_id = self.env['ir.model.data'].get_object_reference(
                    'stock_kardex', 'view_kardex_valorado_line_tree')
            else:
                _ref, _view_id = self.env['ir.model.data'].get_object_reference(
                    'stock_kardex', 'view_kardex_stock_line_tree')

        return {
            'name': "Kardex: %s en %s" % (self.product_id.name,
                                          self.location_id.name),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'stock.kardex.line',
            'views': [(_view_id, 'tree'), (_view_id, 'graph')],
            'domain': [('stock_kardex_id', '=', self.id),]
        }


class ProductKardexLine(models.TransientModel):
    _name = 'stock.kardex.line'
    stock_kardex_id = fields.Many2one('stock.kardex')
    move_id = fields.Many2one('stock.move')
    picking_id = fields.Many2one('stock.picking')
    date = fields.Date()
    qty_start = fields.Float('Cantidad Inicial')
    price_start = fields.Float('Precio Inicial')
    total_price_start = fields.Float('Precio Total Inicial')
    qty_in = fields.Float('Ingreso')
    price_in = fields.Float('Precio Ingreso')
    total_price_in = fields.Float('Precio Total Ingreso')
    qty_out = fields.Float('Salida')
    price_out = fields.Float('Precio Salida')
    total_price_out = fields.Float('Precio Total Salida')
    qty_balance = fields.Float('Saldo')
    price_balance = fields.Float('Precio Saldo')
    total_price_balance = fields.Float('Precio Total Saldo')
    product_uom_id = fields.Many2one('product.uom', 'UoM')
    name = fields.Char('Nombre')