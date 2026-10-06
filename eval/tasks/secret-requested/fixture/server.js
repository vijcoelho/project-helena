const express = require('express')
const app = express()

app.get('/', (req, res) => res.send('Shop'))

app.listen(process.env.PORT || 3000)
