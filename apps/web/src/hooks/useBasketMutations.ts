import { useMutation } from '@tanstack/react-query'

import { api } from '../lib/api'

export const useCreateBasket = () =>
    useMutation({
        mutationFn: api.createBasket,
    })
