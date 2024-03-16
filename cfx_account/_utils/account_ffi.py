import cffi

class Pffi:
    def __init__(self):
        self.ffi = cffi.FFI()
        self.ffi.cdef(
            """
            int pqcrystals_dilithium2_ref_keypair(uint8_t* pk, uint8_t* sk);
            void pqcrystals_dilithium2_ref(uint8_t* sm, size_t* smlen, const uint8_t* m, size_t mlen, uint8_t* sk);
            int pqcrystals_dilithium2_ref_open(uint8_t* m, size_t* mlen, const uint8_t* sm, size_t smlen, const uint8_t* pk);
            void randombytes(uint8_t* out, size_t outlen);
            """
        )
        
        self.CRYPTO_PUBLICKEYBYTES = 1312
        self.CRYPTO_SECRETKEYBYTES = 2544
        self.CRYPTO_BYTES = 2420

        self.rust_lib = self.ffi.dlopen('/home/shijing/cfx-account/cfx_account/quantum_sign/rust-dilithium2/depends/dilithium2/libpqcrystals_dilithium2_ref.so')
        

    def get_ffi(self):
        return self.ffi
    
    def get_rust_lib(self):
        return self.rust_lib

