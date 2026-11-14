resource "aws_route_table" "dmz_public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.phase2_tags, {
    Name    = "${var.phase2_project_name}-dmz-public-rt"
    Segment = "dmz"
  })
}

resource "aws_route_table_association" "dmz_public" {
  subnet_id      = aws_subnet.segments["dmz"].id
  route_table_id = aws_route_table.dmz_public.id
}
