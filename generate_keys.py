from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_key_pair():
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    # Save private key
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    with open("vps_key", "wb") as f:
        f.write(pem_private)
        
    # Generate public key
    public_key = private_key.public_key()
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )
    
    with open("vps_key.pub", "wb") as f:
        f.write(pem_public)

    print("Keys generated successfully: vps_key and vps_key.pub")

if __name__ == "__main__":
    generate_key_pair()
