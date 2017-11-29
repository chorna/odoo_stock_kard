{
    'name': 'Stock Kardex',
    'author': 'chorna',
    'version': '1.0',
    'category': 'Stock',
    'description': """
        Kardex del Producto en una Ubicación
    """,
    'depends': ['stock',],
    'data': [
        'views/kardex_lines.xml',
        'wizard/stock_kardex_views.xml',
        'views/menu.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
